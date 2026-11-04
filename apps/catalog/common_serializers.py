"""
Serializer pieces shared across admin and seller listing serializers —
nothing here is reachable through a URL on its own.
"""

from rest_framework import serializers

from .models import ListingMedia


class ListingMediaSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Listing's detail page. Gallery files are written
    through the listing-files APIs (apps.catalog.listing_files)."""

    class Meta:
        model = ListingMedia
        fields = ["id", "media_type", "media_path", "media_url"]


def _cheapest_sku(listing):
    """The active SKU with the lowest price right now — what a listing page
    shows as "from ...". For a gig this is the lowest rate; `price_type` says
    what the rate is for (an hour, a day, a week, a month, or a fixed price).
    Uses prefetched SKUs when available."""
    active = [sku for sku in listing.skus.all() if sku.is_active]
    return min(active, key=lambda sku: (sku.effective_price(), sku.price)) if active else None


class ListingFromPriceMixin:
    """Read-only `price` / `discounted_price` on a listing: the original and
    the currently charged price of its cheapest active SKU (null when there is
    none). The real prices live on `skus`."""

    def get_price(self, obj):
        sku = _cheapest_sku(obj)
        return str(sku.price) if sku else None

    def get_discounted_price(self, obj):
        sku = _cheapest_sku(obj)
        return str(sku.effective_price()) if sku else None

    def get_price_type(self, obj):
        sku = _cheapest_sku(obj)
        return sku.price_type if sku else None
