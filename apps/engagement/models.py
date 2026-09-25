"""
Reviews & Favourites (DB Redesign doc, Section 3.10).

`Review` ties back to a specific completed `Order` (not a bare listing id),
making an uncompleted-order review structurally awkward to create by
accident. `Favourite` drops the five mutually-exclusive legacy shop-id
columns in favor of one `listing`. Replaces reviews, favourits.
"""

from django.db import models

from apps.core.models import AuditedModel


class Review(AuditedModel):
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="reviews", db_column="orderId"
    )
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="reviews", db_column="reviewerId"
    )
    # Denormalized alongside order for fast "all reviews for this listing" queries.
    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.CASCADE, related_name="reviews", db_column="listingId"
    )
    rating = models.PositiveSmallIntegerField()
    content = models.TextField(null=True, blank=True)
    seller_reply = models.TextField(db_column="sellerReply", null=True, blank=True)

    class Meta:
        db_table = "reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review #{self.pk} ({self.rating}*)"


class Favourite(AuditedModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="favourites", db_column="userId"
    )
    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.CASCADE, related_name="favourited_by", db_column="listingId"
    )

    class Meta:
        db_table = "favourites"
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="unique_favourite_per_user_per_listing"),
        ]

    def __str__(self):
        return f"Favourite: user {self.user_id} / listing {self.listing_id}"
