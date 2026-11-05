"""
Serializers for the seller's own endpoints (`/api/v1/seller/...`). See
seller/views.py.
"""

from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin
from apps.core.models import ActorType

from ..common_serializers import (
    KYC_LOCKED_MEDIA_FOR, KYC_MEDIA_FOR, MediaSyncMixin, ProfilePicUploadMixin, SellerInfoSerializer,
    SellerMediaSerializer, validate_kyc_files,
)
from ..models import Seller, SellerInfo, SellerMedia
from ..profile_log import record_profile_changes, snapshot


class SellerSelfSerializer(
    LocationConsistencyMixin, MediaSyncMixin, ProfilePicUploadMixin, serializers.ModelSerializer
):
    """A seller's own profile (`/seller/me/`) — what they may read and edit.

    Editable: name, photo, both addresses, location, skills/education/experience/
    interest, the business profile (`info`) and documents. Not editable: email and
    phone (sending a different value is a 400), status, verification, the request
    flag. Once verified, NID and birth-certificate documents are locked. Every real
    change is written to the profile change log."""

    profile_pic = serializers.ImageField(write_only=True, required=False)
    remove_profile_pic = serializers.BooleanField(write_only=True, required=False, default=False)
    media = SellerMediaSerializer(many=True, read_only=True)
    media_for = serializers.ListField(
        child=serializers.ChoiceField(choices=[(item.value, item.label) for item in KYC_MEDIA_FOR]),
        write_only=True, required=False, default=list,
    )
    media_file = serializers.ListField(child=serializers.FileField(), write_only=True, required=False, default=list)
    media_delete_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False, default=list)
    info = serializers.JSONField(write_only=True, required=False)
    business_info = SellerInfoSerializer(source="info", read_only=True)
    can_operate = serializers.BooleanField(read_only=True)
    can_edit_profile = serializers.BooleanField(read_only=True)

    media_model = SellerMedia
    media_fk_name = "seller"

    class Meta:
        model = Seller
        fields = [
            "id", "name", "email", "phone",
            "profile_pic", "remove_profile_pic", "profile_pic_url",
            "present_address", "permanent_address", "country", "state", "city", "thana",
            "skills", "education", "experience", "interest",
            "media", "media_for", "media_file", "media_delete_ids", "info", "business_info",
            "verification_status", "verification_note", "status", "is_seller_request",
            "can_operate", "can_edit_profile",
            "created_at", "requested_at",
        ]
        read_only_fields = [
            "profile_pic_url", "verification_status", "verification_note", "status",
            "is_seller_request", "created_at", "requested_at",
        ]
        extra_kwargs = {
            "present_address": {"allow_null": False, "allow_blank": False},
            "permanent_address": {"allow_null": False, "allow_blank": False},
            "country": {"allow_null": False},
            "state": {"allow_null": False},
            "city": {"allow_null": False},
        }

    def validate_email(self, value):
        if value != self.instance.email:
            raise serializers.ValidationError("Email cannot be changed.")
        return value

    def validate_phone(self, value):
        if value != self.instance.phone:
            raise serializers.ValidationError("Phone cannot be changed.")
        return value

    def validate_media_file(self, files):
        return validate_kyc_files(files)

    def validate_info(self, value):
        info_serializer = SellerInfoSerializer(data=value)
        info_serializer.is_valid(raise_exception=True)
        return info_serializer.validated_data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        seller = self.instance
        adding = attrs.get("media_for", [])
        deleting = list(SellerMedia.objects.filter(seller=seller, id__in=attrs.get("media_delete_ids", [])))
        if seller.verification_status == Seller.VerificationStatus.VERIFIED:
            touches_identity = any(kind in KYC_LOCKED_MEDIA_FOR for kind in adding) or any(
                doc.media_for in KYC_LOCKED_MEDIA_FOR for doc in deleting
            )
            if touches_identity:
                raise serializers.ValidationError(
                    {"media_for": "Your identity documents (NID, birth certificate) are locked after verification. "
                                  "Ask an admin to change them."}
                )
        if any(doc.media_for == SellerMedia.MediaFor.NID for doc in deleting):
            kept = SellerMedia.objects.filter(seller=seller, media_for=SellerMedia.MediaFor.NID).exclude(
                id__in=[doc.id for doc in deleting]
            ).count()
            if kept + adding.count(SellerMedia.MediaFor.NID) < 1:
                raise serializers.ValidationError(
                    {"media_for": "At least one NID document is required. Upload the new NID in the same request."}
                )
        return attrs

    def update(self, instance, validated_data):
        info_data = validated_data.pop("info", None)
        before = snapshot(instance)
        instance = super().update(instance, validated_data)
        if info_data:
            SellerInfo.objects.update_or_create(seller=instance, defaults=info_data)
        record_profile_changes(
            instance, before,
            validated_data.get("updated_by"), validated_data.get("updater_type", ActorType.SELLER),
            validated_data.get("updater_name"),
        )
        return instance


class SellerResubmitSerializer(serializers.Serializer):
    """Body of `POST /seller/me/resubmit/` — an optional message for the reviewer."""

    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class SellerChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_current_password(self, value):
        if not check_password(value, self.context["seller"].password):
            raise serializers.ValidationError("Incorrect password.")
        return value

    def validate_new_password(self, value):
        try:
            run_password_validators(value, self.context["seller"])
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": "The new password must be different from the current one."})
        return attrs
