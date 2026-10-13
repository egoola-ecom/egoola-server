"""
The listing info change log: who changed what on a listing, with the value
before and the value after. The listing twin of apps/accounts/profile_log.py.

Usage: take a `snapshot()` before an update, apply the update, then call
`record_listing_changes()`. It writes ONE ListingInfoChangeLog row holding only
the things that really changed (nothing is written when nothing changed). The
same code serves the seller's own edits and an admin's edits.

Tracked: the text fields and their Bangla versions, category, brand, measurement,
owner, location, service details, `attributes`, and three groups shown as whole
lists: `price_tiers`, `skus` (prices, discount windows, active flag, options; NOT
stock or reserved quantity, which change all the time) and `media`.
Not tracked: status and note (see ListingStatusChangeLog), slug, stock.
"""

from datetime import timezone
from decimal import Decimal

from .models import ListingInfoChangeLog, ListingMedia, ListingPriceTier, ListingSku

SIMPLE_FIELDS = (
    "catalog_type", "listing_type", "posted_by_role",
    "title", "title_bn", "description", "description_bn",
    "model", "origin", "origin_bn", "warranty", "warranty_bn", "currency",
    "price_type", "hourly_rate", "delivery_days", "urgent",
    "package_includes", "package_includes_bn", "available_from", "available_to",
    "min_order_qty", "condition_note", "condition_note_bn", "attributes",
)
RELATED_FIELDS = ("category", "brand", "measurement", "seller", "buyer", "country", "state", "city", "thana")


def _plain(value):
    """JSON-safe: money as text, dates as ISO text."""
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        # Compare moments, not time-zone spellings: the same instant read from
        # the database (UTC) and set from a request (local time) must be equal.
        if getattr(value, "tzinfo", None) is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    return value


def _place(obj):
    return None if obj is None else {"id": obj.pk, "name": getattr(obj, "name", None) or str(obj)}


def snapshot(listing):
    """The listing's tracked data as plain values (the related lists are read
    fresh from the database so prefetched data never goes stale)."""
    data = {field: _plain(getattr(listing, field)) for field in SIMPLE_FIELDS}
    for field in RELATED_FIELDS:
        data[field] = _place(getattr(listing, field))

    data["price_tiers"] = [
        {
            "min_qty": tier.min_qty, "max_qty": tier.max_qty,
            "price": _plain(tier.price), "discounted_price": _plain(tier.discounted_price),
            "listing_sku": tier.listing_sku_id,
        }
        for tier in ListingPriceTier.objects.filter(listing=listing).order_by("min_qty", "id")
    ]
    skus = ListingSku.objects.filter(listing=listing).order_by("id").prefetch_related(
        "variants__attribute", "variants__attribute_value"
    )
    data["skus"] = [
        {
            "id": sku.id, "sku": sku.sku,
            "price": _plain(sku.price), "discounted_price": _plain(sku.discounted_price),
            "discount_start_date": _plain(sku.discount_start_date), "discount_end_date": _plain(sku.discount_end_date),
            "is_active": sku.is_active,
            "options": sorted(f"{v.attribute.name}: {v.attribute_value.name}" for v in sku.variants.all()),
        }
        for sku in skus
    ]
    data["media"] = [
        {"id": media.id, "media_type": media.media_type, "media_url": media.media_url}
        for media in ListingMedia.objects.filter(listing=listing).order_by("id")
    ]
    return data


def diff(before, after):
    """(changed_fields, previous, new): only the keys whose value differs."""
    changed, previous, new = [], {}, {}
    for key in before:
        if before[key] != after[key]:
            changed.append(key)
            previous[key], new[key] = before[key], after[key]
    return changed, previous, new


def record_listing_changes(listing, before, actor_id, actor_type, actor_name):
    """Write the log row for the change from `before` to the listing's current
    state. Returns the row, or None when nothing tracked changed."""
    changed, previous, new = diff(before, snapshot(listing))
    if not changed:
        return None
    return ListingInfoChangeLog.objects.create(
        listing=listing,
        changed_fields=changed,
        previous_data=previous,
        new_data=new,
        created_by=actor_id,
        creator_type=actor_type,
        creator_name=actor_name,
    )
