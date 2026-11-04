"""
Serializers for the seller's job board (`/api/v1/seller/jobs/...`): browsing
open jobs and the seller's own history on each. See
docs/buyer/buyer-api-guide.md / the seller guide for the full contract.
"""

from rest_framework import serializers

from .models import Category, Listing


class _CategoryBrief(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_bn", "slug"]


class SellerJobListSerializer(serializers.ModelSerializer):
    category = _CategoryBrief(read_only=True)
    budget = serializers.SerializerMethodField()
    bid_count = serializers.IntegerField(read_only=True)
    my_bid_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "status", "budget",
            "delivery_days", "urgent", "bid_count", "my_bid_count", "created_at",
        ]

    def get_budget(self, obj):
        skus = [s for s in obj.skus.all() if s.is_active]
        if not skus:
            return None
        cheapest = min(skus, key=lambda s: s.effective_price())
        return {"price": str(cheapest.effective_price()), "price_type": cheapest.price_type}


class SellerJobDetailSerializer(SellerJobListSerializer):
    my_bids = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(SellerJobListSerializer.Meta):
        fields = SellerJobListSerializer.Meta.fields + [
            "description", "description_bn", "package_includes", "package_includes_bn",
            "available_from", "available_to", "location", "my_bids",
        ]

    def get_location(self, obj):
        return {
            level: ({"id": getattr(obj, f"{level}_id"), "name": getattr(obj, level).name} if getattr(obj, f"{level}_id") else None)
            for level in ("country", "state", "city", "thana")
        }

    def get_my_bids(self, obj):
        # Imported here to avoid a hard import cycle between catalog and bidding.
        from apps.bidding.seller.serializers import SellerBidListSerializer

        seller = self.context["request"].user
        mine = [b for b in obj.bids.all() if b.bidder_id == seller.id]
        return SellerBidListSerializer(mine, many=True).data
