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

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin

from .models import Category, Listing, ListingSku
from .serializers import ListingSkuSerializer

SERVICE_FIELDS = (
    "delivery_days", "urgent", "package_includes", "package_includes_bn", "available_from", "available_to",
)

# Transitions a buyer may make directly. open_for_bidding -> in_progress only
# ever happens when a bid is accepted (a later step, never set here).
_OPEN_STATES = (Listing.Status.OPEN_FOR_BIDDING, Listing.Status.DRAFT, Listing.Status.PENDING)
_ALLOWED_NEXT = {
    Listing.Status.OPEN_FOR_BIDDING: {Listing.Status.OPEN_FOR_BIDDING, Listing.Status.DRAFT, Listing.Status.CANCELLED},
    Listing.Status.DRAFT: {Listing.Status.DRAFT, Listing.Status.PENDING, Listing.Status.CANCELLED},
    Listing.Status.PENDING: {Listing.Status.PENDING, Listing.Status.OPEN_FOR_BIDDING, Listing.Status.CANCELLED},
    Listing.Status.IN_PROGRESS: {Listing.Status.IN_PROGRESS, Listing.Status.COMPLETED},
}


def _generate_slug(title):
    """Same algorithm as the admin/seller listing serializer's own
    _generate_slug — kept as a small standalone copy rather than importing a
    bound method off that unrelated class."""
    base = slugify(title) or "job"
    slug = base
    suffix = 1
    while Listing.all_objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


def create_job(buyer, actor, validated_data):
    """Shared by the buyer's own create (`buyer == actor`) and the admin
    endpoint's create-on-a-buyer's-behalf (`actor` is the admin, stamped as
    creator; `buyer` is whoever the job is actually for)."""
    skus_data = validated_data.pop("skus")
    with transaction.atomic():
        job = Listing.objects.create(
            **validated_data,
            slug=_generate_slug(validated_data["title"]),
            catalog_type=Listing.CatalogType.SERVICE,
            posted_by_role=Listing.PostedByRole.BUYER_REQUEST,
            buyer=buyer,
            status=Listing.Status.OPEN_FOR_BIDDING,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )
        for row in skus_data:
            ListingSku.objects.create(
                listing=job, price_type=row.get("price_type") or ListingSku.PriceType.FIXED,
                price=row["price"], description=row.get("description"), description_bn=row.get("description_bn"),
                created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
            )
    return job


def update_job(instance, actor, validated_data):
    """Shared by the buyer's own edit and the admin endpoint's edit — the
    buyer a job belongs to is never reassigned, so both only ever need
    `actor` (who's making the change, for the audit stamp and the
    cancel/complete cascades)."""
    # Imported here to avoid a hard import cycle between catalog and bidding.
    from apps.bidding.services import cancel_job_bids, complete_job

    skus_data = validated_data.pop("skus", None)
    new_status = validated_data.get("status")

    with transaction.atomic():
        if new_status == Listing.Status.PENDING and instance.status != Listing.Status.PENDING:
            validated_data["requested_at"] = timezone.now()
        if "title" in validated_data and slugify(validated_data["title"]) != slugify(instance.title):
            validated_data["slug"] = _generate_slug(validated_data["title"])
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.updated_by, instance.updater_type, instance.updater_name = actor.id, actor.actor_type, actor.name
        instance.save()

        if new_status == Listing.Status.CANCELLED:
            cancel_job_bids(instance, actor)
        elif new_status == Listing.Status.COMPLETED:
            complete_job(instance, actor)

        if skus_data is not None:
            existing = {sku.id: sku for sku in instance.skus.all()}
            for row in skus_data:
                sku_id = row.pop("id", None)
                if sku_id and sku_id in existing:
                    sku = existing[sku_id]
                    for field, value in row.items():
                        setattr(sku, field, value)
                    sku.updated_by, sku.updater_type, sku.updater_name = actor.id, actor.actor_type, actor.name
                    sku.save()
                else:
                    ListingSku.objects.create(
                        listing=instance, price_type=row.get("price_type") or ListingSku.PriceType.FIXED,
                        price=row["price"], description=row.get("description"), description_bn=row.get("description_bn"),
                        created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
                    )
            # Existing SKUs not mentioned are left as-is (never deleted — see ListingSku's own docstring).
    return instance


class BuyerJobSkuSerializer(ListingSkuSerializer):
    """A job's budget: reuses the same SKU shape a product/gig uses, minus
    the parts that only make sense for something actually for sale."""

    class Meta(ListingSkuSerializer.Meta):
        fields = [f for f in ListingSkuSerializer.Meta.fields if f not in ("variants", "stock_qty", "reserved_qty")]


class _CategoryBrief(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_bn", "slug"]


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
        from apps.bidding.buyer_serializers import BuyerBidBriefSerializer

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
