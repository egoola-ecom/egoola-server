"""
Mixins and serializers shared across admin, seller, and public (self-
registration) account serializers — nothing here is reachable through a
URL on its own.
"""

import os

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin
from config.storage import delete_upload, infer_media_type, save_upload

from .models import SellerInfo, SellerMedia, User


class PasswordWriteMixin:
    """Hashes `password` on write instead of storing it as plain text.

    The field itself is `required=False` — on a full PUT, a client
    updating an unrelated field (say, `status`) shouldn't be forced to
    resend the current plaintext password just to satisfy a "required"
    check. It's still mandatory when actually creating a new Admin/Seller/
    Buyer, enforced below rather than via the field itself, since "required
    on create, optional on update" isn't something a single field option
    can express.

    OTP/reset/remember-token fields are deliberately left out of every
    serializer below (not just made read-only) — there is no OTP or
    password-reset flow built yet, so exposing them would be dead, unsafe
    surface area. They come back once that flow is built.
    """

    def validate_password(self, value):
        # The project's AUTH_PASSWORD_VALIDATORS (min length 8, not a common
        # or all-numeric password) — only runs when a password is sent.
        try:
            run_password_validators(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required when creating a new record."})
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        return super().update(instance, validated_data)


class ProfilePicUploadMixin:
    """The client sends a `profile_pic` file, never a path/URL — this
    uploads it to storage and computes `profile_pic_path`/`profile_pic_url`
    itself, so those two stay read-only from the client's point of view."""

    def _apply_profile_pic(self, instance, profile_pic):
        # `media_fk_name` ("admin"/"seller"/"buyer") already exists on the
        # serializers that mix this in (see MediaSyncMixin) — reused here
        # so profile pics and media land under the same folder name,
        # rather than Django's internal model name ("user" for Buyer).
        path, url = save_upload(profile_pic, "profile-pics", getattr(self, "media_fk_name", self.Meta.model._meta.model_name))
        old_path = instance.profile_pic_path
        instance.profile_pic_path = path
        instance.profile_pic_url = url
        instance.save(update_fields=["profile_pic_path", "profile_pic_url"])
        if old_path and old_path != path:
            # The replaced picture's file is no longer needed.
            transaction.on_commit(lambda: delete_upload(old_path))

    def create(self, validated_data):
        profile_pic = validated_data.pop("profile_pic", None)
        instance = super().create(validated_data)
        if profile_pic is not None:
            self._apply_profile_pic(instance, profile_pic)
        return instance

    def update(self, instance, validated_data):
        profile_pic = validated_data.pop("profile_pic", None)
        instance = super().update(instance, validated_data)
        if profile_pic is not None:
            self._apply_profile_pic(instance, profile_pic)
        return instance


class MediaSyncMixin:
    """Media (NID, certificates, gallery images...) is managed entirely
    through this parent's own create/update — there's no separate media
    endpoint any more. The client sends `media_for` + `media_file` pairs
    (matched by position — the Nth media_for goes with the Nth media_file)
    to add media, and `media_delete_ids` to remove existing rows.

    There's no in-place edit of an existing file: replacing one is a
    delete + a new upload, which avoids needing separate partial-update
    semantics for something that doesn't really have a partial form.
    """

    media_model = None
    media_fk_name = None

    def validate(self, attrs):
        media_for_list = attrs.get("media_for") or []
        media_file_list = attrs.get("media_file") or []
        if len(media_for_list) != len(media_file_list):
            raise serializers.ValidationError(
                {"media_for": "Provide exactly one media_for value for each media_file, in the same order."}
            )
        return super().validate(attrs)

    def _create_media(self, instance, media_for_list, media_file_list):
        for media_for, uploaded_file in zip(media_for_list, media_file_list):
            path, url = save_upload(uploaded_file, self.media_fk_name, media_for)
            self.media_model.objects.create(
                **{self.media_fk_name: instance},
                media_for=media_for,
                media_type=infer_media_type(uploaded_file),
                media_path=path,
                media_url=url,
            )

    def create(self, validated_data):
        media_for_list = validated_data.pop("media_for", [])
        media_file_list = validated_data.pop("media_file", [])
        validated_data.pop("media_delete_ids", None)  # nothing to delete yet on create
        instance = super().create(validated_data)
        self._create_media(instance, media_for_list, media_file_list)
        return instance

    def update(self, instance, validated_data):
        media_for_list = validated_data.pop("media_for", [])
        media_file_list = validated_data.pop("media_file", [])
        delete_ids = validated_data.pop("media_delete_ids", [])
        instance = super().update(instance, validated_data)
        if delete_ids:
            instance.media.filter(id__in=delete_ids).delete()
        self._create_media(instance, media_for_list, media_file_list)
        return instance


class OptionalBuyerEmailMixin:
    """A buyer's email is optional: an empty value means "no email" (stored as
    NULL, so two buyers without one do not clash), and a given one must be new
    (upper / lower case count as the same email, like at login)."""

    def validate_email(self, value):
        if value in (None, ""):
            return None
        clash = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("buyer with this email already exists.")
        return value


class SellerMediaSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Seller's detail page (admin and self). Writes
    happen through the parent serializer's media_for/media_file/
    media_delete_ids instead."""

    class Meta:
        model = SellerMedia
        fields = ["id", "media_type", "media_for", "media_path", "media_url"]


class SellerInfoSerializer(LocationConsistencyMixin, serializers.ModelSerializer):
    class Meta:
        model = SellerInfo
        fields = [
            "business_type", "main_product", "owner_name",
            "employees_range", "annual_revenue", "established_year", "description",
            "public_email", "whatsapp", "facebook", "wechat", "skype",
            "country", "state", "city", "thana",
        ]


# Identity documents sent at self-registration: pictures or PDFs only, a size
# cap per file, and a cap on how many (storage is shared and the endpoint is
# public).
KYC_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
KYC_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
KYC_MAX_FILE_BYTES = 5 * 1024 * 1024
KYC_MAX_FILES = 10
KYC_MEDIA_FOR = [
    SellerMedia.MediaFor.NID,
    SellerMedia.MediaFor.BIRTH_CERTIFICATE,
    SellerMedia.MediaFor.CERTIFICATE,
    SellerMedia.MediaFor.OTHER,
]
# Documents that prove identity: a seller cannot change these once verified.
KYC_LOCKED_MEDIA_FOR = (SellerMedia.MediaFor.NID, SellerMedia.MediaFor.BIRTH_CERTIFICATE)


def validate_kyc_files(files):
    """Type, size and count rules for identity documents (sign-up and `/seller/me/`)."""
    if len(files) > KYC_MAX_FILES:
        raise serializers.ValidationError(f"Upload at most {KYC_MAX_FILES} documents.")
    for uploaded in files:
        extension = os.path.splitext(uploaded.name)[1].lower()
        content_type = (uploaded.content_type or "").lower()
        if extension not in KYC_ALLOWED_EXTENSIONS or content_type not in KYC_ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError(f"{uploaded.name}: only JPG, PNG, WEBP or PDF files are accepted.")
        if uploaded.size > KYC_MAX_FILE_BYTES:
            raise serializers.ValidationError(
                f"{uploaded.name}: each file must be {KYC_MAX_FILE_BYTES // (1024 * 1024)} MB or smaller."
            )
    return files
