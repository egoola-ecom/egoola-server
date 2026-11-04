"""
Serializers for a buyer's own job postings (`/api/v1/buyer/jobs/...`). A job
is a `Listing` with `catalog_type=service`, `posted_by_role=buyer_request`,
`buyer=<the poster>`, `seller=None` — see `apps.catalog.kinds` and
`Listing.Status`'s docstring for the full state machine. See
docs/buyer/buyer-api-guide.md.

Unlike a product or a gig, a job skips admin moderation entirely (no
draft/pending/approved/rejected/changes_requested review) — it goes straight
to `open_for_bidding`. `draft`/`pending` are reused here only for the job's
own pause/reopen cycle, not for moderation.
"""

from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin

from ..admin_api.serializers import BuyerJobSkuSerializer, _CategoryBrief
from ..job_services import _ALLOWED_NEXT, create_job, update_job
from ..models import Category, Listing, ListingSku

SERVICE_FIELDS = (
    "delivery_days", "urgent", "package_includes", "package_includes_bn", "available_from", "available_to",
)

class BuyerJobListSerializer(serializers.ModelSerializer):
    category = _CategoryBrief(read_only=True)
    budget = serializers.SerializerMethodField()
    bid_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "status", "budget", "bid_count",
            "delivery_days", "urgent", "created_at", "updated_at",
        ]

    def get_budget(self, obj):
        skus = [s for s in obj.skus.all() if s.is_active]
        if not skus:
            return None
        cheapest = min(skus, key=lambda s: s.effective_price())
        return {"price": str(cheapest.effective_price()), "price_type": cheapest.price_type}


class BuyerJobDetailSerializer(BuyerJobListSerializer):
    skus = BuyerJobSkuSerializer(many=True, read_only=True)
    accepted_bid = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(BuyerJobListSerializer.Meta):
        fields = BuyerJobListSerializer.Meta.fields + [
            "description", "description_bn", "package_includes", "package_includes_bn",
            "available_from", "available_to", "location", "skus", "accepted_bid", "note",
        ]

    def get_location(self, obj):
        return {
            level: ({"id": getattr(obj, f"{level}_id"), "name": getattr(obj, level).name} if getattr(obj, f"{level}_id") else None)
            for level in ("country", "state", "city", "thana")
        }

    def get_accepted_bid(self, obj):
        # Imported here to avoid a hard import cycle between catalog and bidding.
        from apps.bidding.buyer.serializers import BuyerBidBriefSerializer

        bid = next((b for b in obj.bids.all() if b.status == b.Status.ACCEPTED), None)
        return BuyerBidBriefSerializer(bid).data if bid else None


class BuyerJobWriteSerializer(LocationConsistencyMixin, serializers.ModelSerializer):
    skus = BuyerJobSkuSerializer(many=True, required=False)

    class Meta:
        model = Listing
        fields = [
            "id", "category", "title", "title_bn", "description", "description_bn",
            "delivery_days", "urgent", "package_includes", "package_includes_bn",
            "available_from", "available_to", "country", "state", "city", "thana",
            "status", "note", "skus",
        ]
        extra_kwargs = {
            "title_bn": {"required": False, "allow_null": True, "allow_blank": True},
            "description_bn": {"required": False, "allow_null": True, "allow_blank": True},
            "status": {"required": False},
        }

    def validate_category(self, value):
        if value.type != Category.CatalogType.SERVICE:
            raise serializers.ValidationError("A job needs a service category.")
        if value.status != Category.Status.ACTIVE:
            raise serializers.ValidationError("This category is inactive.")
        return value

    def validate_skus(self, value):
        seen = set()
        for row in value:
            price_type = row.get("price_type") or ListingSku.PriceType.FIXED
            if price_type in seen:
                raise serializers.ValidationError(f"Two budget options use the same price type ({price_type}).")
            seen.add(price_type)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance

        if instance is None:
            if not attrs.get("skus"):
                raise serializers.ValidationError({"skus": "A job needs at least one budget option."})
            attrs.pop("status", None)  # always starts open_for_bidding, never client-chosen
            return attrs

        current = instance.status
        new_status = attrs.get("status", current)
        if current not in _ALLOWED_NEXT:
            raise serializers.ValidationError(
                {"status": "This job can no longer be edited (it's completed or cancelled)."}
            )
        if new_status not in _ALLOWED_NEXT[current]:
            raise serializers.ValidationError(
                {"status": f"Cannot move a job from '{current}' to '{new_status}'."}
            )
        if current == Listing.Status.IN_PROGRESS and new_status != Listing.Status.COMPLETED:
            # Only the complete action is allowed here; every other field is admin-only once hired.
            non_status_fields = set(attrs) - {"status"}
            if non_status_fields:
                raise serializers.ValidationError(
                    "This job has been hired — only an admin can edit it now (you may still mark it complete)."
                )
        return attrs

    def create(self, validated_data):
        actor = self.context["request"].user
        return create_job(buyer=actor, actor=actor, validated_data=validated_data)

    def update(self, instance, validated_data):
        actor = self.context["request"].user
        return update_job(instance, actor, validated_data)
