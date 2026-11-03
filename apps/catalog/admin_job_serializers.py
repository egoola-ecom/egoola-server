"""
Serializers for the admin job panel (`/api/v1/catalog/jobs/...`). Same job
shape and state machine as a buyer's own `/buyer/jobs/` (see
buyer_job_serializers.py, whose `create_job`/`update_job`/`_ALLOWED_NEXT`
this reuses) — "admin can do everything" here means: create/edit a job on
any buyer's behalf, and one extra transition only an admin may make:
`in_progress -> cancelled` (with a mandatory reason), since normally only
`completed` is reachable from there.
"""

from rest_framework import serializers

from apps.accounts.models import User
from apps.core.location import LocationConsistencyMixin

from .buyer_job_serializers import (
    BuyerJobSkuSerializer,
    _ALLOWED_NEXT,
    _CategoryBrief,
    create_job,
    update_job,
)
from .models import Category, Listing, ListingSku

_ADMIN_ALLOWED_NEXT = {
    **_ALLOWED_NEXT,
    Listing.Status.IN_PROGRESS: _ALLOWED_NEXT[Listing.Status.IN_PROGRESS] | {Listing.Status.CANCELLED},
}


class _BuyerBrief(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "phone", "email"]


class AdminJobListSerializer(serializers.ModelSerializer):
    category = _CategoryBrief(read_only=True)
    buyer = _BuyerBrief(read_only=True)
    budget = serializers.SerializerMethodField()
    bid_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "buyer", "status", "budget", "bid_count",
            "delivery_days", "urgent", "created_at", "updated_at",
        ]

    def get_budget(self, obj):
        skus = [s for s in obj.skus.all() if s.is_active]
        if not skus:
            return None
        cheapest = min(skus, key=lambda s: s.effective_price())
        return {"price": str(cheapest.effective_price()), "price_type": cheapest.price_type}


class AdminJobDetailSerializer(AdminJobListSerializer):
    skus = BuyerJobSkuSerializer(many=True, read_only=True)
    accepted_bid = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta(AdminJobListSerializer.Meta):
        fields = AdminJobListSerializer.Meta.fields + [
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
        from apps.bidding.buyer_serializers import BuyerBidBriefSerializer

        bid = next((b for b in obj.bids.all() if b.status == b.Status.ACCEPTED), None)
        return BuyerBidBriefSerializer(bid).data if bid else None


class AdminJobWriteSerializer(LocationConsistencyMixin, serializers.ModelSerializer):
    skus = BuyerJobSkuSerializer(many=True, required=False)

    class Meta:
        model = Listing
        fields = [
            "id", "buyer", "category", "title", "title_bn", "description", "description_bn",
            "delivery_days", "urgent", "package_includes", "package_includes_bn",
            "available_from", "available_to", "country", "state", "city", "thana",
            "status", "note", "skus",
        ]
        extra_kwargs = {
            "buyer": {"required": False},  # required on create only — see validate()
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
            if not attrs.get("buyer"):
                raise serializers.ValidationError({"buyer": "Say which buyer this job is for."})
            if not attrs.get("skus"):
                raise serializers.ValidationError({"skus": "A job needs at least one budget option."})
            attrs.pop("status", None)  # always starts open_for_bidding, never client-chosen
            return attrs

        attrs.pop("buyer", None)  # never reassigned after creation
        current = instance.status
        new_status = attrs.get("status", current)
        if current not in _ADMIN_ALLOWED_NEXT:
            raise serializers.ValidationError(
                {"status": "This job can no longer be edited (it's completed or cancelled)."}
            )
        if new_status not in _ADMIN_ALLOWED_NEXT[current]:
            raise serializers.ValidationError(
                {"status": f"Cannot move a job from '{current}' to '{new_status}'."}
            )
        if current == Listing.Status.IN_PROGRESS and new_status == Listing.Status.CANCELLED and not attrs.get("note"):
            raise serializers.ValidationError({"note": "A reason is required to cancel a hired job."})
        if current == Listing.Status.IN_PROGRESS and new_status not in (Listing.Status.COMPLETED, Listing.Status.CANCELLED):
            non_status_fields = set(attrs) - {"status"}
            if non_status_fields:
                raise serializers.ValidationError(
                    "This job has been hired — only status changes (complete/cancel) are allowed now."
                )
        return attrs

    def create(self, validated_data):
        buyer = validated_data.pop("buyer")
        actor = self.context["request"].user
        return create_job(buyer=buyer, actor=actor, validated_data=validated_data)

    def update(self, instance, validated_data):
        actor = self.context["request"].user
        return update_job(instance, actor, validated_data)
