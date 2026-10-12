"""
The seller profile change log: who changed what on a seller's profile, with the
value before and the value after.

Usage: take a `snapshot()` before an update, apply the update, then call
`record_profile_changes()`. It writes ONE SellerProfileChangeLog row holding only
the fields that really changed (nothing is written when nothing changed). The
same code serves the seller's own edits (`/seller/me/`), the admin's edits
(`/accounts/sellers/{id}/`) and a password change.

Tracked: name, email, phone, both addresses, country/state/city/thana, profile
picture, skills/education/experience/interest, the business profile (as one
`business_info` object) and the uploaded documents (as one `documents` list).
Not tracked: status, verification (see SellerVerificationLog), wallet, flags.

The password is never stored: a changed password shows up as `password` with the
placeholder value `[hidden]` on both sides.
"""

from .models import SellerInfo, SellerMedia, SellerProfileChangeLog

SIMPLE_FIELDS = (
    "name", "email", "phone", "present_address", "permanent_address",
    "skills", "education", "experience", "interest",
)
LOCATION_FIELDS = ("country", "state", "city", "thana")
INFO_TEXT_FIELDS = (
    "business_type", "main_product", "owner_name", "employees_range", "annual_revenue",
    "established_year", "description", "public_email", "whatsapp", "facebook", "wechat", "skype",
)
HIDDEN = "[hidden]"


def _place(obj):
    """A location as {id, name}: the name is saved too, so the log stays readable if it is renamed later."""
    return None if obj is None else {"id": obj.pk, "name": obj.name}


def snapshot(seller):
    """The seller's tracked data as plain values (queries the database fresh for
    the business profile and the documents, so prefetched data never goes stale)."""
    data = {field: getattr(seller, field) for field in SIMPLE_FIELDS}
    for field in LOCATION_FIELDS:
        data[field] = _place(getattr(seller, field))
    data["profile_pic"] = seller.profile_pic_url
    data["password"] = seller.password
    info = SellerInfo.objects.select_related("country", "state", "city", "thana").filter(seller=seller).first()
    if info is None:
        data["business_info"] = None
    else:
        business = {field: getattr(info, field) for field in INFO_TEXT_FIELDS}
        for field in LOCATION_FIELDS:
            business[field] = _place(getattr(info, field))
        data["business_info"] = business
    data["documents"] = [
        {"id": media.id, "media_for": media.media_for, "media_type": media.media_type, "media_url": media.media_url}
        for media in SellerMedia.objects.filter(seller=seller).order_by("id")
    ]
    return data


def diff(before, after):
    """(changed_fields, previous, new) — only keys whose value differs."""
    changed, previous, new = [], {}, {}
    for key in before:
        if before[key] == after[key]:
            continue
        changed.append(key)
        if key == "password":
            previous[key] = new[key] = HIDDEN
        elif key == "business_info" and before[key] is not None and after[key] is not None:
            # Inside the business profile, show only the parts that changed.
            parts = [name for name in before[key] if before[key][name] != after[key][name]]
            previous[key] = {name: before[key][name] for name in parts}
            new[key] = {name: after[key][name] for name in parts}
        else:
            previous[key], new[key] = before[key], after[key]
    return changed, previous, new


def record_profile_changes(seller, before, actor_id, actor_type, actor_name):
    """Write the log row for the change from `before` to the seller's current
    state. Returns the row, or None when nothing tracked changed."""
    changed, previous, new = diff(before, snapshot(seller))
    if not changed:
        return None
    return SellerProfileChangeLog.objects.create(
        seller=seller,
        changed_fields=changed,
        previous_data=previous,
        new_data=new,
        created_by=actor_id,
        creator_type=actor_type,
        creator_name=actor_name,
    )
