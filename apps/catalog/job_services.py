"""
Shared job (buyer request) lifecycle logic — create/update and the status
transition rules, used by both the buyer's own job endpoints and the
admin "do everything on a buyer's behalf" endpoints, so the two surfaces
can never drift apart on what creating or editing a job actually does.
"""

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import Listing, ListingSku

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
