"""
The listing thumbnail: one cover picture per listing (product or gig), kept
apart from the gallery (`ListingMedia`). It has its own endpoints:

    PUT    .../{id}/thumbnail/   upload or replace (multipart field `image`)
    DELETE .../{id}/thumbnail/   remove it

on `/catalog/listings/`, `/catalog/gigs/` (admin) and `/seller/listings/`,
`/seller/gigs/` (seller). A thumbnail change is a content change like any other
edit: it goes in the info change log, and when a seller does it on a rejected /
changes-requested listing the listing goes back to `pending`, exactly as saving
the listing would. Old files are deleted from storage.
"""

import os

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.models import ActorType
from config.storage import delete_upload, save_upload

from .listing_log import record_listing_changes, snapshot
from .models import Listing, ListingStatusChangeLog

THUMBNAIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
THUMBNAIL_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
THUMBNAIL_MAX_BYTES = 10 * 1024 * 1024


class ThumbnailUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, image):
        extension = os.path.splitext(image.name)[1].lower()
        content_type = (image.content_type or "").lower()
        if extension not in THUMBNAIL_EXTENSIONS or content_type not in THUMBNAIL_CONTENT_TYPES:
            raise serializers.ValidationError("Only JPG, PNG or WEBP pictures are accepted.")
        if image.size > THUMBNAIL_MAX_BYTES:
            raise serializers.ValidationError(f"The picture must be {THUMBNAIL_MAX_BYTES // (1024 * 1024)} MB or smaller.")
        return image


class ThumbnailViewSetMixin:
    """Adds `PUT` / `DELETE .../{id}/thumbnail/` to a listing viewset. The viewset's
    `get_queryset()` must return the row locked and limited to what the caller may
    touch for the `thumbnail` action (see `lock_for_edit_actions`)."""

    # A seller's edit sends a rejected / changes-requested listing back to the admin.
    thumbnail_resubmits = False

    @action(
        detail=True, methods=["put", "delete"], url_path="thumbnail",
        parser_classes=[MultiPartParser, FormParser], filter_backends=[], pagination_class=None,
        serializer_class=ThumbnailUploadSerializer,  # the upload body, for the API docs
    )
    def thumbnail(self, request, pk=None):
        actor = request.user
        stamp = {
            "updated_by": getattr(actor, "id", None),
            "updater_type": getattr(actor, "actor_type", ActorType.SYSTEM),
            "updater_name": getattr(actor, "name", None),
        }
        new_path = None
        with transaction.atomic():
            listing = self.get_object()
            before = snapshot(listing)
            old_path = listing.image_path
            if request.method == "PUT":
                serializer = ThumbnailUploadSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                new_path, listing.image_url = save_upload(serializer.validated_data["image"], "listing", "thumbnails")
                listing.image_path = new_path
            else:
                listing.image_path = None
                listing.image_url = None
            changed_fields = ["image_path", "image_url"]
            for key, value in stamp.items():
                setattr(listing, key, value)
            changed_fields += list(stamp)

            resubmitted = self.thumbnail_resubmits and listing.status in (
                Listing.Status.REJECTED, Listing.Status.CHANGES_REQUESTED, Listing.Status.DRAFT
            )
            if resubmitted:
                listing.status = Listing.Status.PENDING
                listing.note = None
                listing.requested_at = timezone.now()
                changed_fields += ["status", "note", "requested_at"]
            listing.save(update_fields=changed_fields + ["updated_at"])
            if resubmitted:
                ListingStatusChangeLog.objects.create(
                    listing=listing, status=listing.status, note=None,
                    created_by=stamp["updated_by"], creator_type=stamp["updater_type"],
                    creator_name=stamp["updater_name"],
                )
            record_listing_changes(listing, before, stamp["updated_by"], stamp["updater_type"], stamp["updater_name"])
            if old_path and old_path != listing.image_path:
                transaction.on_commit(lambda: delete_upload(old_path))

        if request.method == "DELETE":
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({
            "image_path": listing.image_path, "image_url": listing.image_url, "status": listing.status,
        })
