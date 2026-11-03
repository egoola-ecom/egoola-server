"""
The side effects of a job/bid status change that reach across both tables
(and into Orders) — shared by the buyer's own actions (apps.bidding.buyer_views)
and the admin "can do everything" endpoints (apps.bidding.admin_views), so the
two surfaces can never drift apart on what accepting, cancelling or
completing actually does.
"""

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Listing
from apps.orders.models import Order, OrderItem

from .models import Bid


def _stamp(instance, actor):
    instance.updated_by, instance.updater_type, instance.updater_name = actor.id, actor.actor_type, actor.name


def accept_bid(job, bid, price_tier, actor):
    """The buyer (or admin, on their behalf) accepts one bid on their job:
    that bid wins, every other live bid on the job is auto-rejected, the job
    moves to `in_progress`, and an Order is created directly (no cart) to
    record the hire. Returns `(bid, order)`."""
    with transaction.atomic():
        bid.accepted_price_tier = price_tier
        bid.status = Bid.Status.ACCEPTED
        bid.actual_start_date = timezone.now()
        _stamp(bid, actor)
        bid.save()

        Bid.objects.filter(
            listing=job, status=Bid.Status.PENDING,
        ).exclude(pk=bid.pk).update(
            status=Bid.Status.REJECTED,
            updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name,
        )

        job.status = Listing.Status.IN_PROGRESS
        _stamp(job, actor)
        job.save()

        order = Order.objects.create(
            buyer=job.buyer, seller=bid.bidder, order_type=Order.OrderType.JOB,
            # in_progress, not accepted: the job itself is already in_progress at this
            # same moment (work starts now — see actual_start_date above), so the
            # order should never sit at "accepted" while work is already underway.
            listing=job, bid=bid, status=Order.Status.IN_PROGRESS,
            subtotal=price_tier.total_price, total=price_tier.total_price, payable=price_tier.total_price,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )
        OrderItem.objects.create(
            order=order, listing=job, title_snapshot=job.title,
            price_snapshot=price_tier.price, price_type_snapshot=price_tier.price_type,
            duration=price_tier.duration, total=price_tier.total_price, subtotal=price_tier.total_price,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )
    return bid, order


def cancel_job_bids(job, actor):
    """A job being cancelled (from any state) takes every *live* bid down
    with it — pending or accepted — as `cancelled`, not `rejected`: nothing
    about those bids was judged, the opportunity just vanished. A bid that
    already lost to another one earlier (`rejected`) stays rejected. If the
    job had an accepted bid with an Order behind it, that Order is cancelled
    too — the hire never happened."""
    live = Bid.objects.filter(listing=job, status__in=(Bid.Status.PENDING, Bid.Status.ACCEPTED))
    accepted_bid_ids = list(live.filter(status=Bid.Status.ACCEPTED).values_list("id", flat=True))
    live.update(
        status=Bid.Status.CANCELLED,
        updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name,
    )
    if accepted_bid_ids:
        Order.objects.filter(bid_id__in=accepted_bid_ids, order_type=Order.OrderType.JOB).update(
            status=Order.Status.CANCELLED, cancelled_reason=job.note,
            updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name,
        )


def admin_reject_accepted_bid(bid, actor, note):
    """Admin-only: undo a hire without cancelling the job itself. The bid
    that was accepted goes to `rejected` (not `cancelled` — this one *was*
    judged, just the other way), its Order is cancelled, and the job reopens
    for bidding. Every bid that auto-rejected earlier when this one was
    accepted stays `rejected` — the sellers may place a fresh bid if they
    want back in, nothing about their old one is restored."""
    with transaction.atomic():
        job = bid.listing
        bid.status = Bid.Status.REJECTED
        bid.accepted_price_tier = None
        bid.note = note
        _stamp(bid, actor)
        bid.save()

        Order.objects.filter(bid=bid, order_type=Order.OrderType.JOB).update(
            status=Order.Status.CANCELLED, cancelled_reason=note,
            updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name,
        )

        job.status = Listing.Status.OPEN_FOR_BIDDING
        _stamp(job, actor)
        job.save()
    return bid


def complete_job(job, actor):
    """A job marked complete carries its accepted bid, and that bid's Order,
    to `completed` with it."""
    bid = Bid.objects.filter(listing=job, status=Bid.Status.ACCEPTED).first()
    if not bid:
        return
    now = timezone.now()
    bid.status = Bid.Status.COMPLETED
    bid.actual_end_date = now
    _stamp(bid, actor)
    bid.save()
    Order.objects.filter(bid=bid, order_type=Order.OrderType.JOB).update(
        status=Order.Status.COMPLETED, completed_at=now,
        updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name,
    )
