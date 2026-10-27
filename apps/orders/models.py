"""
Orders, Order Items & Payments (DB Redesign doc, Section 3.7).

Every purchase flow — buying goods, hiring a service, or accepting a job
bid — collapses around three core tables: `Order` (the transaction
envelope, tagged by `order_type`), `OrderItem` (line items), and `Payment`
(every money movement, tagged by `purpose`), with `Cart`/`CartItem` feeding
into them at checkout. Replaces carts (kept, split into header+items),
sales, orders, billings, shippings, delivery_costs, order_pays,
service_orders, hireds, hire_pays, payments, payment_requests, balances,
refund_histories, transactions, commissions, commission_payments,
seller_payments.
"""

from decimal import Decimal

from django.db import models

from apps.core.models import AuditedModel, CatalogType


class Cart(AuditedModel):
    """A buyer's cart, one per (buyer, cart_type): a product cart and a service
    (gig) cart never mix, since they checkout through different gateways
    (Stripe vs bKash — see Order). A cart is never reused: once it becomes an
    order (`order` is set, `is_active` turns False) it is kept as-is, items and
    all, as the record of what that order was built from. A later add-to-cart
    for the same buyer and type creates a fresh, active cart."""

    CatalogType = CatalogType

    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="carts", db_column="buyerId"
    )
    cart_type = models.CharField(db_column="cartType", max_length=10, choices=CatalogType.choices)
    is_active = models.BooleanField(db_column="isActive", default=True)
    order = models.OneToOneField(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_cart",
        db_column="orderId",
    )

    class Meta:
        db_table = "carts"
        constraints = [
            models.UniqueConstraint(
                fields=["buyer", "cart_type"], condition=models.Q(is_active=True),
                name="unique_active_cart_per_buyer_type",
            ),
        ]

    def __str__(self):
        return f"Cart for buyer {self.buyer_id} ({self.cart_type}, {'active' if self.is_active else 'closed'})"

    @property
    def subtotal(self):
        """Sum of every line's `line_subtotal`, worked out live (see CartItem).
        Call with `items` already prefetched — this iterates `self.items.all()`,
        it does not run its own query."""
        total = Decimal("0.00")
        for item in self.items.all():
            if item.line_subtotal is not None:
                total += item.line_subtotal
        return total


class CartItem(AuditedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", db_column="cartId")
    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.CASCADE, related_name="cart_items", db_column="listingId"
    )
    listing_sku = models.ForeignKey(
        "catalog.ListingSku", on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items",
        db_column="listingSkuId",
    )
    # Null for a gig: a gig has no quantity; the buyer chooses how many price-type
    # units (hours, days, ...) instead (`duration`). A product always has a qty.
    qty = models.IntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "cartItems"

    @property
    def units(self):
        """How many of the unit price this line is worth: qty for a product,
        duration for a gig — whichever one this line actually uses."""
        return self.qty if self.qty is not None else self.duration

    @property
    def unit_price(self):
        """The price charged right now (the discount price while one is
        running) — never stored, so it always reflects the current sale."""
        return self.listing_sku.effective_price() if self.listing_sku_id else None

    @property
    def line_subtotal(self):
        units = self.units
        if self.listing_sku_id is None or units is None:
            return None
        return self.unit_price * units

    @property
    def is_available(self):
        """False once something has changed since this was added: the SKU
        went inactive, the listing is no longer approved or was deleted, or
        stock can no longer cover `qty`. The line is kept either way — only
        checkout needs to decide what to do about it."""
        sku, listing = self.listing_sku, self.listing
        if not sku or not sku.is_active or listing.status != listing.Status.APPROVED or listing.deleted_at:
            return False
        if self.qty is not None and sku.stock_qty is not None:
            return sku.stock_qty - sku.reserved_qty >= self.qty
        return True


class Address(AuditedModel):
    """A delivery-address snapshot, either attached to one specific order or
    saved standalone against a buyer for reuse (a loosely-typed reference,
    `addressable_type` + `addressable_id`, matching the redesign doc's
    polymorphic pairing rather than a real FK to either table)."""

    class AddressableType(models.TextChoices):
        ORDER = "order", "Order"
        USER = "user", "User"

    addressable_type = models.CharField(db_column="addressableType", max_length=10, choices=AddressableType.choices)
    addressable_id = models.BigIntegerField(db_column="addressableId")

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    country = models.ForeignKey("geography.Country", on_delete=models.PROTECT, db_column="countryId")
    state = models.ForeignKey("geography.State", on_delete=models.PROTECT, db_column="stateId")
    city = models.ForeignKey("geography.City", on_delete=models.PROTECT, db_column="cityId")
    thana = models.ForeignKey("geography.Thana", on_delete=models.PROTECT, db_column="thanaId")
    address_line1 = models.CharField(db_column="addressLine1", max_length=255)
    address_line2 = models.CharField(db_column="addressLine2", max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "addresses"

    def __str__(self):
        return f"{self.name} - {self.address_line1}"


class Order(AuditedModel):
    class OrderType(models.TextChoices):
        PRODUCT = "product", "Product"
        SERVICE = "service", "Service"
        JOB = "job", "Job"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        DISPUTED = "disputed", "Disputed"

    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="orders", db_column="buyerId"
    )
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.PROTECT, related_name="orders", db_column="sellerId"
    )
    order_type = models.CharField(db_column="orderType", max_length=10, choices=OrderType.choices)
    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders",
        db_column="listingId",
    )
    bid = models.ForeignKey(
        "bidding.Bid", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders",
        db_column="bidId",
    )
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders", db_column="addressId"
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)

    # Sum of the items' amounts. `total` is before any product discount (original
    # prices), `subtotal` after it (the prices actually charged), so the product
    # discount is `total - subtotal`. `discount` is an extra order-level discount
    # (a coupon, for example). `payable` is what the buyer actually has to pay:
    # `subtotal + deliveryCost - discount`.
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_cost = models.DecimalField(db_column="deliveryCost", max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payable = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(db_column="commissionRate", max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(db_column="commissionAmount", max_digits=12, decimal_places=2)

    expected_delivery_at = models.DateTimeField(db_column="expectedDeliveryAt", null=True, blank=True)
    completed_at = models.DateTimeField(db_column="completedAt", null=True, blank=True)
    cancelled_reason = models.TextField(db_column="cancelledReason", null=True, blank=True)
    confirmation_secret = models.CharField(db_column="confirmationSecret", max_length=64, null=True, blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.order_type})"


class OrderItem(AuditedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", db_column="orderId")
    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.PROTECT, related_name="order_items", db_column="listingId"
    )
    # The exact SKU bought: its options (size, colour) are the variants of this SKU.
    listing_sku = models.ForeignKey(
        "catalog.ListingSku", on_delete=models.PROTECT, null=True, blank=True, related_name="order_items",
        db_column="listingSkuId",
    )
    title_snapshot = models.CharField(db_column="titleSnapshot", max_length=255)
    # The original unit price (product) or rate (gig) when it was ordered.
    price_snapshot = models.DecimalField(db_column="priceSnapshot", max_digits=12, decimal_places=2)
    # Gig only: what the rate was for (hourly, daily, weekly, monthly or fixed).
    price_type_snapshot = models.CharField(db_column="priceTypeSnapshot", max_length=10, null=True, blank=True)
    # Product: how many. Null for a gig.
    qty = models.IntegerField(null=True, blank=True)
    # Gig: how many price-type units the buyer chose (3 with hourly = 3 hours). Null for a product.
    duration = models.PositiveIntegerField(null=True, blank=True)
    deliverable_path = models.CharField(db_column="deliverablePath", max_length=255, null=True, blank=True)
    # The line amount with the original price: price x qty (product) or rate x duration (gig).
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # The same with the price actually charged (the discounted price while a discount runs, else the
    # normal price).
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "orderItems"


class Payment(AuditedModel):
    """Every money movement against an order, or a standalone seller
    withdrawal, in one auditable ledger filtered by `purpose` — replaces
    payments, payment_requests, balances, refund_histories, transactions,
    commissions, commission_payments, seller_payments."""

    class UserType(models.TextChoices):
        SELLER = "seller", "Seller"
        USER = "user", "User"

    class Purpose(models.TextChoices):
        CHECKOUT_PAYMENT = "checkout_payment", "Checkout Payment"
        SELLER_PAYOUT = "seller_payout", "Seller Payout"
        COMMISSION_PAYMENT = "commission_payment", "Commission Payment"
        REFUND = "refund", "Refund"

    class Direction(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments", db_column="orderId"
    )
    # Polymorphic reference into sellers or users depending on user_type,
    # per the DB Redesign doc's "Bug fixed at the schema level" note — kept
    # as a plain id + type pair rather than two nullable FKs.
    user_id = models.BigIntegerField(db_column="userId")
    user_type = models.CharField(db_column="userType", max_length=10, choices=UserType.choices)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50)
    gateway_txn_id = models.CharField(db_column="gatewayTxnId", max_length=100, null=True, blank=True)
    payout_account_number = models.CharField(
        db_column="payoutAccountNumber", max_length=100, null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "user_type", "purpose"], name="payments_user_purpose_idx"),
        ]

    def __str__(self):
        return f"{self.purpose} {self.amount} ({self.status})"
