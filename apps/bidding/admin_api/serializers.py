"""
Serializers for the admin bid panel (`/api/v1/bidding/bids/...`): oversight
of every bid, plus "do everything" — create or edit a bid on any seller's
behalf. Same price-tier contract as a seller's own `/seller/bids/` (see
..common_serializers.BidPriceTierSerializer and ..services.create_bid/
update_bid, which this reuses). Accepting and rejecting-an-accepted-bid are
their own actions (see admin_api/views.py), not a generic PATCH.
"""

from rest_framework import serializers

from apps.accounts.models import Seller
from apps.catalog.models import Listing

from ..common_serializers import BidPriceTierSerializer
from ..models import Bid, BidPriceTier
from ..services import create_bid, update_bid


class _JobBrief(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ["id", "title", "title_bn", "slug", "status", "buyer"]


class _BidderBrief(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ["id", "name", "phone"]


class AdminBidListSerializer(serializers.ModelSerializer):
    job = _JobBrief(source="listing", read_only=True)
    bidder = _BidderBrief(read_only=True)
    price_tiers = BidPriceTierSerializer(many=True, read_only=True)
    accepted_price_tier = BidPriceTierSerializer(read_only=True)

    class Meta:
        model = Bid
        fields = [
            "id", "job", "bidder", "status", "description", "proposed_start", "proposed_end",
            "price_tiers", "accepted_price_tier", "created_at", "updated_at",
        ]


class AdminBidDetailSerializer(AdminBidListSerializer):
    class Meta(AdminBidListSerializer.Meta):
        fields = AdminBidListSerializer.Meta.fields + [
            "actual_start_date", "actual_end_date", "note",
        ]


class AdminBidWriteSerializer(serializers.ModelSerializer):
    price_tiers = BidPriceTierSerializer(many=True, required=False)

    class Meta:
        model = Bid
        fields = ["id", "listing", "bidder", "description", "proposed_start", "proposed_end", "status", "price_tiers"]
        extra_kwargs = {
            "listing": {"required": False},  # required on create only — see validate()
            "bidder": {"required": False},
            "status": {"required": False},
        }

    def validate_price_tiers(self, value):
        seen = set()
        for row in value:
            price_type = row.get("price_type") or BidPriceTier.PriceType.FIXED
            if "id" not in row and price_type in seen:
                raise serializers.ValidationError(f"Two tiers use the same price type ({price_type}).")
            seen.add(price_type)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None:
            job = attrs.get("listing")
            bidder = attrs.get("bidder")
            if not job or job.posted_by_role != Listing.PostedByRole.BUYER_REQUEST:
                raise serializers.ValidationError({"listing": "Say which job this bid is for."})
            if not bidder:
                raise serializers.ValidationError({"bidder": "Say which seller this bid is for."})
            if job.status != Listing.Status.OPEN_FOR_BIDDING:
                raise serializers.ValidationError("This job isn't open for bidding.")
            if not attrs.get("price_tiers"):
                raise serializers.ValidationError({"price_tiers": "A bid needs at least one price option."})
            live = Bid.objects.filter(
                listing=job, bidder=bidder, status__in=(Bid.Status.PENDING, Bid.Status.ACCEPTED),
            ).exists()
            if live:
                raise serializers.ValidationError("This seller already has a live bid on this job.")
            attrs.pop("status", None)  # always starts pending, never client-chosen
            return attrs

        attrs.pop("listing", None)  # never reassigned after creation
        attrs.pop("bidder", None)
        if self.instance.status != Bid.Status.PENDING:
            raise serializers.ValidationError("This bid can no longer be edited.")
        new_status = attrs.get("status", Bid.Status.PENDING)
        if new_status not in (Bid.Status.PENDING, Bid.Status.CANCELLED):
            raise serializers.ValidationError(
                {"status": "Use the accept/reject actions for those — a plain edit can only cancel a pending bid."}
            )
        return attrs

    def create(self, validated_data):
        job = validated_data.pop("listing")
        bidder = validated_data.pop("bidder")
        actor = self.context["request"].user
        return create_bid(job=job, bidder=bidder, actor=actor, validated_data=validated_data)

    def update(self, instance, validated_data):
        actor = self.context["request"].user
        return update_bid(instance, actor, validated_data)
