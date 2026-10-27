"""
Serializers for the buyer's own wishlist (`/api/v1/buyer/favourites/...`).
See buyer_views.py and docs/buyer-api-guide.md.
"""

from rest_framework import serializers

from apps.catalog.models import Listing
from apps.catalog.public_listings import PublicGigListSerializer, PublicProductListSerializer, buyer_visible_listings

from .models import Favourite


class FavouriteSerializer(serializers.ModelSerializer):
    """The saved listing, shown exactly as it appears while browsing (same
    row shape as the public product/gig lists) — a product or a gig picks
    its own serializer by `catalog_type`, since the two show different
    fields (price range vs. price-per-unit)."""

    catalog_type = serializers.CharField(source="listing.catalog_type", read_only=True)
    listing = serializers.SerializerMethodField()

    class Meta:
        model = Favourite
        fields = ["id", "catalog_type", "listing", "created_at"]

    def get_listing(self, obj):
        is_product = obj.listing.catalog_type == Listing.CatalogType.PRODUCT
        serializer_class = PublicProductListSerializer if is_product else PublicGigListSerializer
        return serializer_class(obj.listing, context=self.context).data


class AddFavouriteSerializer(serializers.Serializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=buyer_visible_listings())
