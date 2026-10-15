"""
Pictures and videos of a listing (a product or a gig): the thumbnail (one cover
picture, `imagePath` / `imageUrl` on the listing) and the gallery (`ListingMedia`).

The listing and gig create / update APIs are JSON only and never touch files.
Files have two APIs for each role, and each works for a product or a gig id:

    Admin   POST  /catalog/listing-files/{listingId}/   add files
            PATCH /catalog/listing-files/{listingId}/   change files
    Seller  POST  /seller/listing-files/{listingId}/    add files (own listings)
            PATCH /seller/listing-files/{listingId}/    change files (own listings)

Both are `multipart/form-data`:

    POST   thumbnail      optional, one image (refused if the listing already has one)
           media_file     optional, repeated, each an image / video / PDF
    PATCH  remove_thumbnail   optional, true / false: delete the current thumbnail
           thumbnail          optional: a new thumbnail; it replaces the old one (deleted)
           remove_media_ids   optional, `1,2,3` (or repeated): gallery ids to delete
           media_file         optional, repeated: gallery files to add

The parts are independent. A request that changes nothing is fine and changes
nothing. Everything is validated before anything is saved: the request either
succeeds as a whole or changes nothing. Files are uploaded before the listing
row is locked (a slow upload must not block a moderation decision), new files
are deleted again if the save fails, and old files are deleted only after the
change is committed.

A change is written in the admin's info change log (`thumbnail`, `media`). It never
changes the listing's status, for an admin or a seller: only saving the listing
itself (create / update) does.
"""

import os

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsActiveVerifiedSellerActor, IsAdminActor
from apps.core.models import ActorType
from config.storage import delete_upload, infer_media_type, save_upload

from .listing_log import record_listing_changes, snapshot
from .models import Listing, ListingMedia
from .serializers import ListingMediaSerializer

THUMBNAIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
THUMBNAIL_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
THUMBNAIL_MAX_BYTES = 10 * 1024 * 1024

# Gallery files: pictures, a short video or a PDF (the same for admin and seller).
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".pdf"}
MEDIA_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "application/pdf"}
# Extra limits for a seller (an admin has none of these).
SELLER_MEDIA_MAX_BYTES = 10 * 1024 * 1024
SELLER_MEDIA_MAX_PER_REQUEST = 10
SELLER_MEDIA_MAX_PER_LISTING = 20


def _truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _media_ids(data, key):
    """`1,2,3`, or the field repeated, as a list of ints (a 400 for anything else)."""
    raw = data.getlist(key) if hasattr(data, "getlist") else [data.get(key)]
    ids = []
    for chunk in raw:
        for part in str(chunk if chunk is not None else "").split(","):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit():
                raise ValidationError({key: f"'{part}' is not a media id."})
            ids.append(int(part))
    return list(dict.fromkeys(ids))


def _check_thumbnail(image):
    extension = os.path.splitext(image.name)[1].lower()
    content_type = (image.content_type or "").lower()
    if extension not in THUMBNAIL_EXTENSIONS or content_type not in THUMBNAIL_CONTENT_TYPES:
        return "Only JPG, PNG or WEBP pictures are accepted."
    if image.size > THUMBNAIL_MAX_BYTES:
        return f"The picture must be {THUMBNAIL_MAX_BYTES // (1024 * 1024)} MB or smaller."
    # A real picture, not just a file with the right name and content type.
    from PIL import Image

    try:
        Image.open(image).verify()
    except Exception:
        return "This file is not a valid image."
    finally:
        image.seek(0)
    return None


def _check_media(files, *, is_seller):
    errors = []
    if is_seller and len(files) > SELLER_MEDIA_MAX_PER_REQUEST:
        errors.append(f"Upload at most {SELLER_MEDIA_MAX_PER_REQUEST} files at a time.")
    for uploaded in files:
        extension = os.path.splitext(uploaded.name)[1].lower()
        content_type = (uploaded.content_type or "").lower()
        if extension not in MEDIA_EXTENSIONS or content_type not in MEDIA_CONTENT_TYPES:
            errors.append(f"{uploaded.name}: only JPG, PNG, WEBP, GIF, MP4 or PDF files are accepted.")
        elif is_seller and uploaded.size > SELLER_MEDIA_MAX_BYTES:
            errors.append(f"{uploaded.name}: each file must be {SELLER_MEDIA_MAX_BYTES // (1024 * 1024)} MB or smaller.")
    return errors


class _ListingFilesView(APIView):
    """Shared by the admin and the seller views below; they only differ in who may call
    and which listings they may reach."""

    parser_classes = [MultiPartParser, FormParser]
    is_seller = False

    def listings(self, request):
        """The listings this caller may reach: products and gigs (a job is not one of them)."""
        return Listing.objects.filter(
            Q(catalog_type=Listing.CatalogType.PRODUCT)
            | Q(catalog_type=Listing.CatalogType.SERVICE, posted_by_role=Listing.PostedByRole.SELLER_OFFER)
        )

    def get_listing(self, request, listing_id):
        listing = self.listings(request).filter(pk=listing_id).first()
        if listing is None:
            raise NotFound("No listing matches the given id.")
        return listing

    def post(self, request, listing_id):
        """Add the thumbnail (if the listing has none) and / or gallery files."""
        return self._apply(request, self.get_listing(request, listing_id), creating=True)

    def patch(self, request, listing_id):
        """Remove / replace the thumbnail, remove gallery files and / or add gallery files."""
        return self._apply(request, self.get_listing(request, listing_id), creating=False)

    # ------------------------------------------------------------------ the work

    def _apply(self, request, listing, creating):
        data, files = request.data, request.FILES
        thumbnail = files.get("thumbnail")
        new_media = files.getlist("media_file")
        remove_thumbnail = not creating and _truthy(data.get("remove_thumbnail", ""))
        remove_ids = [] if creating else _media_ids(data, "remove_media_ids")

        # 1) Validate everything before anything is saved.
        errors = {}
        if thumbnail is not None:
            problem = _check_thumbnail(thumbnail)
            if problem:
                errors["thumbnail"] = [problem]
            elif creating and listing.image_path:
                errors["thumbnail"] = ["This listing already has a thumbnail. Use the update API (PATCH) to replace it."]
        media_errors = _check_media(new_media, is_seller=self.is_seller)
        existing_ids = set(listing.media.values_list("id", flat=True))
        unknown = [i for i in remove_ids if i not in existing_ids]
        if unknown:
            errors["remove_media_ids"] = [f"Not a file of this listing: {', '.join(map(str, unknown))}."]
        if self.is_seller and new_media and not media_errors:
            keeping = len(existing_ids - set(remove_ids))
            if keeping + len(new_media) > SELLER_MEDIA_MAX_PER_LISTING:
                media_errors.append(f"A listing can have at most {SELLER_MEDIA_MAX_PER_LISTING} files.")
        if media_errors:
            errors["media_file"] = media_errors
        if errors:
            raise ValidationError(errors)

        if not (thumbnail is not None or new_media or remove_thumbnail or remove_ids):
            return Response(
                self._state(listing), status=status.HTTP_201_CREATED if creating else status.HTTP_200_OK
            )

        # 2) Upload before taking the row lock; new files are removed again if anything fails.
        actor = request.user
        stamp = {
            "id": getattr(actor, "id", None),
            "type": getattr(actor, "actor_type", ActorType.SYSTEM),
            "name": getattr(actor, "name", None),
        }
        saved_paths = []
        try:
            new_thumbnail = None
            if thumbnail is not None:
                new_thumbnail = save_upload(thumbnail, "listing", "thumbnails")
                saved_paths.append(new_thumbnail[0])
            saved_media = []
            for uploaded in new_media:
                path, url = save_upload(uploaded, "listing", str(listing.id))
                saved_paths.append(path)
                saved_media.append((uploaded, path, url))

            with transaction.atomic():
                try:
                    listing = Listing.objects.select_for_update(of=("self",)).get(pk=listing.pk)
                except Listing.DoesNotExist:
                    raise NotFound("No listing matches the given id.")
                before = snapshot(listing)
                old_thumbnail = listing.image_path
                changed = False

                if creating and thumbnail is not None and old_thumbnail:  # saved by someone else meanwhile
                    raise ValidationError(
                        {"thumbnail": ["This listing already has a thumbnail. Use the update API (PATCH) to replace it."]}
                    )
                if new_thumbnail is not None:
                    listing.image_path, listing.image_url = new_thumbnail
                    changed = True
                elif remove_thumbnail and old_thumbnail:
                    listing.image_path = listing.image_url = None
                    changed = True

                if remove_ids:
                    # Row by row: each delete removes its file from storage once this commits.
                    for media in listing.media.filter(id__in=remove_ids):
                        media.delete()
                        changed = True
                for uploaded, path, url in saved_media:
                    ListingMedia.objects.create(
                        listing=listing, media_type=infer_media_type(uploaded), media_path=path, media_url=url,
                        created_by=stamp["id"], creator_type=stamp["type"], creator_name=stamp["name"],
                    )
                    changed = True

                if changed:
                    fields = ["image_path", "image_url", "updated_by", "updater_type", "updater_name", "updated_at"]
                    listing.updated_by, listing.updater_type, listing.updater_name = stamp["id"], stamp["type"], stamp["name"]
                    listing.save(update_fields=fields)
                    record_listing_changes(listing, before, stamp["id"], stamp["type"], stamp["name"])
                    if old_thumbnail and old_thumbnail != listing.image_path:
                        transaction.on_commit(lambda: delete_upload(old_thumbnail))
        except Exception:
            for path in saved_paths:
                delete_upload(path)  # nothing was saved: do not leave the new files behind
            raise

        return Response(
            self._state(listing), status=status.HTTP_201_CREATED if creating else status.HTTP_200_OK
        )

    @staticmethod
    def _state(listing):
        return {
            "image_path": listing.image_path,
            "image_url": listing.image_url,
            "media": ListingMediaSerializer(listing.media.all().order_by("id"), many=True).data,
            "status": listing.status,
        }


class AdminListingFilesView(_ListingFilesView):
    """Admin: files of any product or gig. `POST` adds, `PATCH` changes (module docstring)."""

    permission_classes = [IsAdminActor]


class SellerListingFilesView(_ListingFilesView):
    """Seller: files of the seller's own products and gigs (a seller who can operate)."""

    permission_classes = [IsActiveVerifiedSellerActor]
    is_seller = True

    def listings(self, request):
        return super().listings(request).filter(seller=request.user)
