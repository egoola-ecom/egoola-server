"""
Serializers for a seller's own bids (`/api/v1/seller/bids/...`,
`/api/v1/seller/jobs/{job_id}/bids/`). See docs/buyer/buyer-api-guide.md /
seller-api-guide.md for the bid lifecycle.

A bid can only be created on a job that's `open_for_bidding`, and only while
this seller has no other *live* (pending or accepted) bid on that same job —
checked here, not in the schema (see Bid's own docstring). Editing works
while the bid is still `pending`: the full `price_tiers` array is
reconciled the same way a listing's `skus` are (match by `id` -> update, no
`id` -> create, an existing tier not mentioned is left alone, never
auto-deleted). The only status move a seller can make directly is
`pending -> cancelled`; acceptance/rejection are the buyer's/admin's call.
"""

from rest_framework import serializers

from apps.catalog.models import Listing

from ..common_serializers import BidPriceTierSerializer
from ..models import Bid, BidPriceTier
from ..services import create_bid, update_bid


class _JobBrief(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ["id", "title", "title_bn", "slug", "status"]


class SellerBidListSerializer(serializers.ModelSerializer):
    job = _JobBrief(source="listing", read_only=True)
    price_tiers = BidPriceTierSerializer(many=True, read_only=True)
    accepted_price_tier = BidPriceTierSerializer(read_only=True)

    class Meta:
        model = Bid
        fields = [
            "id", "job", "status", "description", "proposed_start", "proposed_end",
            "price_tiers", "accepted_price_tier", "created_at", "updated_at",
        ]


class SellerBidDetailSerializer(SellerBidListSerializer):
    class Meta(SellerBidListSerializer.Meta):
        fields = SellerBidListSerializer.Meta.fields + [
            "actual_start_date", "actual_end_date", "note",
        ]


class SellerBidWriteSerializer(serializers.ModelSerializer):
    price_tiers = BidPriceTierSerializer(many=True, required=False)

    class Meta:
        model = Bid
        fields = ["id", "description", "proposed_start", "proposed_end", "status", "price_tiers"]
        extra_kwargs = {"status": {"required": False}}

    def validate_price_tiers(self, value):
        seen = set()
        for row in value:
            # A row updating an existing tier (has `id`) may omit price_type;
            # only a brand-new row's effective type (defaulted below) matters here.
            price_type = row.get("price_type") or BidPriceTier.PriceType.FIXED
            if "id" not in row and price_type in seen:
                raise serializers.ValidationError(f"Two tiers use the same price type ({price_type}).")
            seen.add(price_type)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None:
            job = self.context["job"]
            if job.status != Listing.Status.OPEN_FOR_BIDDING:
                raise serializers.ValidationError("This job isn't open for bidding.")
            if not attrs.get("price_tiers"):
                raise serializers.ValidationError({"price_tiers": "A bid needs at least one price option."})
            seller = self.context["request"].user
            live = Bid.objects.filter(
                listing=job, bidder=seller, status__in=(Bid.Status.PENDING, Bid.Status.ACCEPTED),
            ).exists()
            if live:
                raise serializers.ValidationError("You already have a live bid on this job.")
            attrs.pop("status", None)  # always starts pending, never client-chosen
            return attrs

        if self.instance.status != Bid.Status.PENDING:
            raise serializers.ValidationError("This bid can no longer be edited.")
        new_status = attrs.get("status", Bid.Status.PENDING)
        if new_status not in (Bid.Status.PENDING, Bid.Status.CANCELLED):
            raise serializers.ValidationError({"status": "You can only cancel a pending bid."})
        return attrs

    def create(self, validated_data):
        actor = self.context["request"].user
        return create_bid(job=self.context["job"], bidder=actor, actor=actor, validated_data=validated_data)

    def update(self, instance, validated_data):
        actor = self.context["request"].user
        return update_bid(instance, actor, validated_data)
