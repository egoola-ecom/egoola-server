"""
Buyer Inquiries / Quote Requests (DB Redesign doc, Section 3.8).

Replaces `simple_reqs`, fixing a data-modeling bug: the legacy `userId`
column actually held the listing's seller, not the buyer submitting the
inquiry. Both parties now get a real, correctly-named foreign key, and
guest inquiries (no buyer account) are supported via the contact* fields.
"""

from django.db import models

from apps.core.models import AuditedModel


class QuoteRequest(AuditedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        RESPONDED = "responded", "Responded"
        CLOSED = "closed", "Closed"

    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.CASCADE, related_name="quote_requests", db_column="listingId"
    )
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="quote_requests",
        db_column="buyerId",
    )
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.CASCADE, related_name="quote_requests", db_column="sellerId"
    )
    qty = models.BigIntegerField()
    message = models.TextField()

    contact_name = models.CharField(db_column="contactName", max_length=255, null=True, blank=True)
    contact_email = models.EmailField(db_column="contactEmail", null=True, blank=True)
    contact_phone = models.CharField(db_column="contactPhone", max_length=32, null=True, blank=True)
    contact_company = models.CharField(db_column="contactCompany", max_length=255, null=True, blank=True)
    contact_city = models.CharField(db_column="contactCity", max_length=255, null=True, blank=True)
    contact_road = models.CharField(db_column="contactRoad", max_length=255, null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)

    class Meta:
        db_table = "quoteRequests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quote request #{self.pk} on listing {self.listing_id}"
