"""
Admin, read-only oversight of buyers' wishlists (`/api/v1/engagement/favourites/...`).
Buyers manage their own list through `apps.engagement.buyer_views` instead —
nothing here ever writes to a favourite. See docs/cart-wishlist-admin-guide.md.
"""

from rest_framework import serializers

from apps.accounts.serializers import BuyerListSerializer
from apps.catalog.models import Listing

from .models import Favourite


class AdminFavouriteListingSerializer(serializers.ModelSerializer):
    """More than a buyer ever sees (status, the seller's own standing) —
    this is for an admin to understand *why* a saved listing might be
    hidden from its buyer, not to browse it."""

    seller = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = ["id", "title", "title_bn", "slug", "catalog_type", "status", "image_url", "seller"]

    def get_seller(self, obj):
        if not obj.seller_id:
            return None
        return {
            "id": obj.seller_id, "name": obj.seller.name,
            "status": obj.seller.status, "verification_status": obj.seller.verification_status,
        }


class AdminFavouriteListSerializer(serializers.ModelSerializer):
    buyer = BuyerListSerializer(read_only=True)
    listing = AdminFavouriteListingSerializer(read_only=True)
    # Annotated on the queryset (Exists subquery) — see apps.engagement.views.
    listing_visible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Favourite
        fields = ["id", "buyer", "listing", "listing_visible", "created_at"]


class AdminFavouriteDetailSerializer(AdminFavouriteListSerializer):
    class Meta(AdminFavouriteListSerializer.Meta):
        fields = AdminFavouriteListSerializer.Meta.fields + [
            "created_by", "creator_type", "creator_name",
            "updated_by", "updater_type", "updater_name", "updated_at",
        ]
