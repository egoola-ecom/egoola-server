"""
Serializers for a buyer looking at the bids on their own job
(`/api/v1/buyer/jobs/{job_id}/bids/...`). Read-only at this step — accepting
a bid is a later step, once a seller can actually place one. See
docs/buyer/buyer-api-guide.md.
"""

from rest_framework import serializers

from apps.accounts.public_views import PublicSellerBriefSerializer

from ..models import Bid, BidPriceTier


class BidPriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = BidPriceTier
        fields = ["id", "price_type", "price", "duration", "description", "total_price"]


class BuyerBidBriefSerializer(serializers.ModelSerializer):
    """Just enough to show "accepted bid" on a job's own detail view."""

    bidder = PublicSellerBriefSerializer(read_only=True)
    accepted_price_tier = BidPriceTierSerializer(read_only=True)

    class Meta:
        model = Bid
        fields = ["id", "bidder", "status", "accepted_price_tier", "created_at"]


class BuyerBidSerializer(BuyerBidBriefSerializer):
    price_tiers = BidPriceTierSerializer(many=True, read_only=True)

    class Meta(BuyerBidBriefSerializer.Meta):
        fields = BuyerBidBriefSerializer.Meta.fields + [
            "description", "proposed_start", "proposed_end",
            "actual_start_date", "actual_end_date", "note", "price_tiers", "updated_at",
        ]
