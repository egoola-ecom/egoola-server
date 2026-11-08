"""
Checkout and the order/payment status machines — the Decimal-safe money
math and the transition rules, shared by the buyer's own checkout/cancel,
the seller's own accept/reject/ship/deliver, and the admin override, so the
three surfaces can never drift on what moving an order (or its payment)
between statuses actually does. Every status move writes its own history
row (OrderStatusChangeHistory / PaymentStatusChangeHistory) — never skipped,
never done anywhere else.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from .models import Address, Cart, Order, OrderItem, OrderStatusChangeHistory, Payment, PaymentStatusChangeHistory

TWO_PLACES = Decimal("0.01")


def money(value):
    """Quantizes to exactly 2 decimal places, half-up — the one place every
    order/payment amount is rounded, so it never happens ad hoc with floor
    or ceil elsewhere."""
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _stamp(instance, actor):
    instance.updated_by, instance.updater_type, instance.updater_name = actor.id, actor.actor_type, actor.name


def _record_order_status(order, previous_status, actor, reason=None):
    OrderStatusChangeHistory.objects.create(
        order=order, user=order.buyer, seller=order.seller,
        previous_status=previous_status, current_status=order.status, reason=reason,
        created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
    )


def _record_payment_status(payment, previous_status, actor):
    PaymentStatusChangeHistory.objects.create(
        order=payment.order, user=payment.order.buyer, seller=payment.order.seller, payment=payment,
        previous_status=previous_status, current_status=payment.status,
        created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
    )


def _mark_checkout_payment_paid(order, actor):
    """COD: the cash is only actually collected on delivery. A no-op once
    the payment has already moved off `due` (e.g. an admin already marked
    it some other way)."""
    payment = order.payment
    if payment is None or payment.status != Payment.Status.DUE:
        return
    previous_status = payment.status
    payment.status = Payment.Status.PAID
    _stamp(payment, actor)
    payment.save()
    _record_payment_status(payment, previous_status, actor)

    order.payment_status = payment.status
    order.save(update_fields=["payment_status"])


# A seller moves an order forward one step at a time, rejecting only while
# it's still pending. Buyer cancellation and the admin override are their
# own functions below, not part of this map.
SELLER_TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.ACCEPTED, Order.Status.REJECTED},
    Order.Status.ACCEPTED: {Order.Status.IN_PROGRESS},
    Order.Status.IN_PROGRESS: {Order.Status.SHIPPED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
}

# A buyer may cancel any time before the seller has shipped it.
BUYER_CANCELLABLE_FROM = {Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.IN_PROGRESS}


def create_order_from_cart(cart, address, payment_gateway, actor):
    """Checkout: cart + a saved address + a payment gateway -> an Order, its
    OrderItems, a Payment (status `due` — only cash on delivery exists), and
    the opening history row on both. `address` is snapshotted onto a fresh
    Address row (editing or deleting the buyer's saved address later never
    changes a past order)."""
    if not cart.is_active:
        raise ValueError("This cart is no longer active.")
    if cart.seller_id is None:
        raise ValueError("A cart with no seller (admin-owned listings) can't be checked out yet.")
    items = list(cart.items.select_related("listing", "listing_sku").all())
    if not items:
        raise ValueError("This cart is empty.")
    problems = [
        f"{item.listing.title}: {item.unavailable_reason}"
        for item in items if item.unavailable_reason
    ]
    if problems:
        raise ValueError(" ".join(problems))

    with transaction.atomic():
        subtotal = money(sum((item.line_subtotal for item in items), Decimal("0.00")))
        total = money(sum((item.listing_sku.price * item.units for item in items), Decimal("0.00")))
        delivery_cost = money(Decimal("0.00"))
        discount = money(Decimal("0.00"))
        payable = money(subtotal + delivery_cost - discount)

        order = Order.objects.create(
            buyer=cart.buyer, seller=cart.seller,
            order_type=Order.OrderType.PRODUCT if cart.cart_type == Cart.CatalogType.PRODUCT else Order.OrderType.SERVICE,
            subtotal=subtotal, delivery_cost=delivery_cost, discount=discount, total=total, payable=payable,
            payment_status=Payment.Status.DUE, payment_gateway=payment_gateway, gateway_slug=payment_gateway.slug,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )
        _record_order_status(order, previous_status=None, actor=actor)

        for item in items:
            sku = item.listing_sku
            units = item.units
            price_snapshot = money(sku.price)
            OrderItem.objects.create(
                order=order, listing=item.listing, listing_sku=sku, title_snapshot=item.listing.title,
                price_snapshot=price_snapshot,
                price_type_snapshot=sku.price_type if item.duration is not None else None,
                qty=item.qty, duration=item.duration,
                total=money(price_snapshot * units), subtotal=money(item.unit_price * units),
                created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
            )

        order_address = Address.objects.create(
            addressable_type=Address.AddressableType.ORDER, addressable_id=order.id,
            name=address.name, phone=address.phone, country=address.country, state=address.state,
            city=address.city, thana=address.thana, address_line1=address.address_line1,
            address_line2=address.address_line2, zip=address.zip,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )

        payment = Payment.objects.create(
            order=order, user_id=actor.id, user_type=Payment.UserType.USER, seller=cart.seller,
            purpose=Payment.Purpose.CHECKOUT_PAYMENT, direction=Payment.Direction.DEBIT,
            amount=payable, method=payment_gateway.name, payment_gateway=payment_gateway,
            gateway_slug=payment_gateway.slug, status=Payment.Status.DUE,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )
        _record_payment_status(payment, previous_status=None, actor=actor)

        order.address, order.payment = order_address, payment
        order.save(update_fields=["address", "payment"])

        cart.order = order
        cart.is_active = False
        _stamp(cart, actor)
        cart.save()

    return order


def seller_set_status(order, new_status, actor, reason=None):
    """The seller's own accept / reject / in_progress / shipped / delivered
    moves — see SELLER_TRANSITIONS. Rejecting needs a reason (buyer-visible)."""
    allowed = SELLER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot move an order from {order.status} to {new_status}.")
    if new_status == Order.Status.REJECTED and not reason:
        raise ValueError("A reason is required to reject an order.")

    with transaction.atomic():
        previous_status = order.status
        if new_status == Order.Status.REJECTED:
            order.rejected_reason = reason
        order.status = new_status
        _stamp(order, actor)
        order.save()
        _record_order_status(order, previous_status, actor, reason=reason if new_status == Order.Status.REJECTED else None)
        if new_status == Order.Status.DELIVERED:
            _mark_checkout_payment_paid(order, actor)
    return order


def buyer_cancel(order, actor, reason=None):
    """The buyer's own cancel — any time before the seller has shipped it."""
    if order.status not in BUYER_CANCELLABLE_FROM:
        raise ValueError("This order can no longer be cancelled.")
    with transaction.atomic():
        previous_status = order.status
        order.status = Order.Status.CANCELLED
        order.cancelled_reason = reason
        _stamp(order, actor)
        order.save()
        _record_order_status(order, previous_status, actor, reason=reason)
    return order


def admin_set_status(order, new_status, actor, reason=None):
    """Admin override: any status, at any time, no transition check."""
    with transaction.atomic():
        previous_status = order.status
        order.status = new_status
        if new_status == Order.Status.REJECTED:
            order.rejected_reason = reason
        elif new_status == Order.Status.CANCELLED:
            order.cancelled_reason = reason
        _stamp(order, actor)
        order.save()
        _record_order_status(order, previous_status, actor, reason=reason)
        if new_status == Order.Status.DELIVERED:
            _mark_checkout_payment_paid(order, actor)
    return order
