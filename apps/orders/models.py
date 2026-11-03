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
from django.utils.text import slugify

from apps.core.models import ActorType, AuditedModel, CatalogType


class Cart(AuditedModel):
    """A buyer's cart, one per (buyer, cart_type, seller): a product cart and a
    service (gig) cart never mix (different checkout gateways — Stripe vs
    bKash), and neither ever mixes two sellers' listings. `Order.seller` is a
    single, required field — an order is always exactly one seller — so this
    keeps a cart in 1:1 shape with the order it will become (`order` below is
    a OneToOneField; a cart spanning sellers could never satisfy that). A
    buyer shopping from several sellers simply has several carts of the same
    type at once, one per seller.

    `seller` is null for an admin-owned listing (no seller) — the constraint
    below treats every null as the same "no seller" bucket (`nulls_distinct`
    =False), not as distinct rows, so there is still only one such cart per
    buyer per type.

    A cart is never reused: once it becomes an order (`order` is set,
    `is_active` turns False) it is kept as-is, items and all, as the record of
    what that order was built from. A later add-to-cart for the same buyer,
    type and seller creates a fresh, active cart."""

    CatalogType = CatalogType

    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="carts", db_column="buyerId"
    )
    # Always "user" for now — `buyer` above is strictly a User row. Carried as
    # a flag (not acted on yet) so a seller buying from another seller's shop
    # can reuse this same cart shape later without another migration.
    buyer_type = models.CharField(
        db_column="buyerType", max_length=10,
        choices=[(ActorType.USER, ActorType.USER.label), (ActorType.SELLER, ActorType.SELLER.label)],
        default=ActorType.USER,
    )
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.CASCADE, null=True, blank=True, related_name="carts",
        db_column="sellerId",
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
                fields=["buyer", "cart_type", "seller"], condition=models.Q(is_active=True),
                nulls_distinct=False,
                name="unique_active_cart_per_buyer_type_seller",
            ),
        ]

    def __str__(self):
        return (
            f"Cart for buyer {self.buyer_id}, seller {self.seller_id} "
            f"({self.cart_type}, {'active' if self.is_active else 'closed'})"
        )

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
        REJECTED = "rejected", "Rejected"
        IN_PROGRESS = "in_progress", "In Progress"
        SHIPPED = "shipped", "Shipped"
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
    # Null until the commission mechanism itself is built (Phase 2's financial
    # oversight API, not started yet) — an order can exist before a rate does.
    commission_rate = models.DecimalField(
        db_column="commissionRate", max_digits=5, decimal_places=2, null=True, blank=True
    )
    commission_amount = models.DecimalField(
        db_column="commissionAmount", max_digits=12, decimal_places=2, null=True, blank=True
    )

    expected_delivery_at = models.DateTimeField(db_column="expectedDeliveryAt", null=True, blank=True)
    completed_at = models.DateTimeField(db_column="completedAt", null=True, blank=True)
    cancelled_reason = models.TextField(db_column="cancelledReason", null=True, blank=True)
    # Required when a seller rejects a product order (buyer-visible); distinct
    # from cancelled_reason — a reject was judged, a cancel is the buyer's own call.
    rejected_reason = models.TextField(db_column="rejectedReason", null=True, blank=True)
    confirmation_secret = models.CharField(db_column="confirmationSecret", max_length=64, null=True, blank=True)

    # Denormalized from the Payment row checkout creates for this order (see
    # services.py) so a list/detail never needs to join into `payments` just
    # to show where the money stands. Kept in sync every time that Payment's
    # own status changes — never written anywhere else.
    payment = models.ForeignKey(
        "Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", db_column="paymentId"
    )
    payment_status = models.CharField(db_column="paymentStatus", max_length=15, null=True, blank=True)
    payment_gateway = models.ForeignKey(
        "PaymentGateway", on_delete=models.PROTECT, null=True, blank=True, related_name="orders",
        db_column="paymentGatewayId",
    )
    gateway_slug = models.CharField(db_column="gatewaySlug", max_length=120, null=True, blank=True)

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


def _generate_gateway_slug(name):
    base = slugify(name) or "gateway"
    slug = base
    suffix = 1
    while PaymentGateway.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


class PaymentGateway(AuditedModel):
    """A way a buyer can pay — admin-managed, checkout picks one by id.
    Only Cash on Delivery is seeded for now; card/mobile-banking gateways
    are added here later without a code change on the checkout side."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon_path = models.CharField(db_column="iconPath", max_length=255, null=True, blank=True)
    icon_url = models.URLField(db_column="iconUrl", max_length=500, null=True, blank=True)
    is_active = models.BooleanField(db_column="isActive", default=True)

    class Meta:
        db_table = "paymentGateways"
        ordering = ["name"]

    def __str__(self):
        return self.name


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
        DUE = "due", "Due"
        INITIATED = "initiated", "Initiated"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"

    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments", db_column="orderId"
    )
    # Polymorphic reference into sellers or users depending on user_type,
    # per the DB Redesign doc's "Bug fixed at the schema level" note — kept
    # as a plain id + type pair rather than two nullable FKs.
    user_id = models.BigIntegerField(db_column="userId")
    user_type = models.CharField(db_column="userType", max_length=10, choices=UserType.choices)
    # Denormalized alongside user_id/user_type — always the order's seller
    # when this payment is against an order; null for a payment that isn't
    # (a standalone payout/commission entry has no single "other side").
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.PROTECT, null=True, blank=True, related_name="payments",
        db_column="sellerId",
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # What's actually been collected/settled through the gateway so far (a
    # bKash-style gateway reports this independently of `amount`, and it's
    # how a partially_paid payment is tracked). Unused for cash on delivery.
    store_amount = models.DecimalField(
        db_column="storeAmount", max_digits=12, decimal_places=2, null=True, blank=True
    )
    # Snapshot of the gateway's name at payment time (survives the gateway
    # being renamed or deactivated later); `payment_gateway` is the live FK,
    # null for a payment that isn't a buyer checkout payment (a payout, say).
    method = models.CharField(max_length=50)
    payment_gateway = models.ForeignKey(
        PaymentGateway, on_delete=models.PROTECT, null=True, blank=True, related_name="payments",
        db_column="paymentGatewayId",
    )
    # Snapshot of the gateway's slug at payment time, same reasoning as `method`.
    gateway_slug = models.CharField(db_column="gatewaySlug", max_length=120, null=True, blank=True)
    gateway_txn_id = models.CharField(db_column="gatewayTxnId", max_length=100, null=True, blank=True)
    payout_account_number = models.CharField(
        db_column="payoutAccountNumber", max_length=100, null=True, blank=True
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DUE)
    meta_data = models.JSONField(db_column="metaData", null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "user_type", "purpose"], name="payments_user_purpose_idx"),
        ]

    def __str__(self):
        return f"{self.purpose} {self.amount} ({self.status})"


class PaymentStatusChangeHistory(models.Model):
    """Append-only history of every status change on a Payment — who
    changed it, from what, to what. Written once when the payment is
    created (previous_status null) and again on every status move; never
    updated or deleted afterwards, so this isn't an AuditedModel."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payment_status_histories", db_column="orderId"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="payment_status_histories", db_column="userId"
    )
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.PROTECT, related_name="payment_status_histories",
        db_column="sellerId",
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="status_histories", db_column="paymentId"
    )
    previous_status = models.CharField(
        db_column="previousStatus", max_length=15, choices=Payment.Status.choices, null=True, blank=True
    )
    current_status = models.CharField(db_column="currentStatus", max_length=15, choices=Payment.Status.choices)

    created_by = models.BigIntegerField(db_column="createdBy", null=True, blank=True)
    creator_type = models.CharField(
        db_column="creatorType", max_length=10, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    creator_name = models.CharField(db_column="creatorName", max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(db_column="createdAt", auto_now_add=True)

    class Meta:
        db_table = "paymentStatusChangeHistories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.payment_id}: {self.previous_status} -> {self.current_status}"


class OrderStatusChangeHistory(models.Model):
    """Append-only history of every status change on an Order — who changed
    it, from what, to what, and why (a reject/cancel reason, at the time of
    that specific move — Order.rejected_reason/cancelled_reason only ever
    hold the latest one). Never updated or deleted, so not an AuditedModel."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_histories", db_column="orderId")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="order_status_histories", db_column="userId"
    )
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.PROTECT, related_name="order_status_histories", db_column="sellerId"
    )
    previous_status = models.CharField(
        db_column="previousStatus", max_length=15, choices=Order.Status.choices, null=True, blank=True
    )
    current_status = models.CharField(db_column="currentStatus", max_length=15, choices=Order.Status.choices)
    reason = models.TextField(null=True, blank=True)

    created_by = models.BigIntegerField(db_column="createdBy", null=True, blank=True)
    creator_type = models.CharField(
        db_column="creatorType", max_length=10, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    creator_name = models.CharField(db_column="creatorName", max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(db_column="createdAt", auto_now_add=True)

    class Meta:
        db_table = "orderStatusChangeHistories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_id}: {self.previous_status} -> {self.current_status}"
