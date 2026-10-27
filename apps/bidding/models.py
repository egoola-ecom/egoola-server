"""
Bidding & Hiring (DB Redesign doc, Section 3.6).

A `Bid` is one seller's negotiation on one job (a `Listing` with
catalog_type=service, posted_by_role=buyer_request). A seller can quote
several price options on the same bid instead of one fixed number — one
`BidPriceTier` per price type, the same header/line-item shape as
Cart/CartItem and Listing/ListingSku elsewhere in this schema. Accepting a
bid means picking exactly one of its tiers (`Bid.accepted_price_tier`); an
accepted bid produces a row in the unified `orders` table (Section 3.7).

Replaces bid_for_services, hireds, hire_pays, service_orders, order_pays
(service side).
"""

from decimal import Decimal

from django.db import models

from apps.core.models import AuditedModel, PriceType


class Bid(AuditedModel):
    """One seller's bid on one job. Never deleted — only its `status`
    changes. A seller can have more than one `Bid` row against the same job
    over time (cancel one, submit a genuinely new one later); what's not
    allowed is two *live* (pending or accepted) bids from the same seller on
    the same job at once — enforced in the API, not the schema, since
    "live" depends on status, not just the (listing, bidder) pair."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.CASCADE, related_name="bids", db_column="listingId"
    )
    bidder = models.ForeignKey(
        "accounts.Seller", on_delete=models.CASCADE, related_name="bids", db_column="bidderId"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # The seller's cover-letter text for the bid as a whole (each price tier
    # has its own, shorter description too — see BidPriceTier).
    description = models.CharField(max_length=300, null=True, blank=True)
    # Same across every tier of this bid — a seller proposes one schedule,
    # not a different one per price option.
    proposed_start = models.DateTimeField(db_column="proposedStart", null=True, blank=True)
    proposed_end = models.DateTimeField(db_column="proposedEnd", null=True, blank=True)
    # When the hired work genuinely started/finished, as opposed to what was
    # proposed above — set once the bid is accepted and work gets underway.
    actual_start_date = models.DateTimeField(db_column="actualStartDate", null=True, blank=True)
    actual_end_date = models.DateTimeField(db_column="actualEndDate", null=True, blank=True)
    # Which of this bid's tiers the buyer (or admin) picked when accepting it.
    # SET_NULL, not PROTECT: nothing in the app ever hard-deletes a tier on
    # its own (same "deactivate, don't delete" rule as everywhere else in this
    # schema) — PROTECT here would only create a delete cycle with BidPriceTier
    # cascading from this same Bid (deleting a Listing -> its Bids -> their
    # tiers, one of which this FK points at) for no real safety benefit.
    accepted_price_tier = models.ForeignKey(
        "bidding.BidPriceTier", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", db_column="acceptedPriceTierId",
    )
    # The admin's mandatory reason for rejecting/cancelling a bid that was
    # already accepted (see apps.catalog.models.Listing.note for the same
    # idea on the job side) — holds the note for the current status only.
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "bids"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bid #{self.pk} on listing {self.listing_id} ({self.status})"


class BidPriceTier(AuditedModel):
    """One price option within a bid — a seller can quote ৳500/hour *and*
    ৳15,000/week on the same bid, for the buyer to choose between. At most
    one tier per price type per bid (the same rule a gig's SKUs follow)."""

    PriceType = PriceType

    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name="price_tiers", db_column="bidId")
    price_type = models.CharField(db_column="priceType", max_length=10, choices=PriceType.choices)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    # How many units of price_type this quote covers (hours, weeks, ...).
    # Meaningless for `fixed`, where it is always 1 so total_price == price.
    duration = models.PositiveIntegerField(default=1)
    description = models.TextField(null=True, blank=True)
    # price * duration — filled in by save(), never taken from the client.
    total_price = models.DecimalField(db_column="totalPrice", max_digits=12, decimal_places=2, blank=True)

    class Meta:
        db_table = "bidPriceTiers"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["bid", "price_type"], name="unique_tier_price_type_per_bid"),
        ]

    def save(self, *args, **kwargs):
        if self.price_type == PriceType.FIXED:
            self.duration = 1
        self.total_price = (self.price or Decimal("0.00")) * self.duration
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.price_type} tier on bid {self.bid_id}"
