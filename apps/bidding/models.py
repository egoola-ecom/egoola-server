"""
Bidding, Hiring & the Job/Order Merge (DB Redesign doc, Section 3.6).

One negotiation table behind every hire, whether it started as a buyer's
open job request or a seller bidding on one. Replaces bid_for_services,
hireds, hire_pays, service_orders, order_pays (service side) — an accepted
bid produces a row in the unified `orders` table (Section 3.7).
"""

from django.db import models

from apps.core.models import AuditedModel


class Bid(AuditedModel):
    class PriceType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        HOURLY = "hourly", "Hourly"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.CASCADE, related_name="bids", db_column="listingId"
    )
    bidder = models.ForeignKey(
        "accounts.Seller", on_delete=models.CASCADE, related_name="bids", db_column="bidderId"
    )
    price_type = models.CharField(db_column="priceType", max_length=10, choices=PriceType.choices)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField(
        db_column="hourlyRate", max_digits=12, decimal_places=2, null=True, blank=True
    )
    hours = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=300)
    proposed_start = models.DateTimeField(db_column="proposedStart", null=True, blank=True)
    proposed_end = models.DateTimeField(db_column="proposedEnd", null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        db_table = "bids"
        ordering = ["-created_at"]
        # One-bid-per-project, enforced at the schema level (DB Redesign 3.6
        # "Bug fixed at the schema level" — was only checked in app code).
        constraints = [
            models.UniqueConstraint(fields=["listing", "bidder"], name="unique_bid_per_listing_per_bidder"),
        ]

    def __str__(self):
        return f"Bid #{self.pk} on listing {self.listing_id}"
