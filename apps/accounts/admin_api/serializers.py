"""
Admin Management, Seller Management, and Buyer Management
(`/api/v1/accounts/{admins,sellers,buyers}/...`). See admin_api/views.py.
"""

from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin
from apps.core.models import ActorType

from ..common_serializers import (
    MediaSyncMixin, OptionalBuyerEmailMixin, PasswordWriteMixin, ProfilePicUploadMixin, SellerInfoSerializer,
    SellerMediaSerializer,
)
from ..models import Admin, AdminMedia, BuyerMedia, Seller, SellerInfo, SellerMedia, SellerProfileChangeLog, SellerVerificationLog, User
from ..profile_log import record_profile_changes, snapshot


class AdminMediaSerializer(serializers.ModelSerializer):
    """Read-only — shown on an Admin's detail page. Writes happen through
    AdminSerializer's media_for/media_file/media_delete_ids instead."""

    class Meta:
        model = AdminMedia
        fields = ["id", "media_type", "media_for", "media_path", "media_url"]


class AdminListSerializer(serializers.ModelSerializer):
    """List page — basic information only. No media (a separate table,
    joining/serializing it for every row in a list is pure overhead the
    list doesn't need) and no geography (same reason). Both are on the
    detail page instead."""

    class Meta:
        model = Admin
        fields = ["id", "name", "email", "mobile", "profile_pic_url", "type", "status", "last_logged_at"]


class AdminSerializer(
    LocationConsistencyMixin, MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin, serializers.ModelSerializer
):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    profile_pic = serializers.ImageField(write_only=True, required=False)
    media = AdminMediaSerializer(many=True, read_only=True)
    media_for = serializers.ListField(
        child=serializers.ChoiceField(choices=AdminMedia.MediaFor.choices),
        write_only=True, required=False, default=list,
    )
    media_file = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, default=list,
    )
    media_delete_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )

    media_model = AdminMedia
    media_fk_name = "admin"

    class Meta:
        model = Admin
        fields = [
            "id", "name", "email", "mobile", "password",
            "profile_pic", "profile_pic_path", "profile_pic_url", "type", "status",
            "skills", "experiences", "interests", "educations",
            "present_address", "permanent_address",
            "country", "state", "city", "thana",
            "last_logged_at",
            "media", "media_for", "media_file", "media_delete_ids",
        ]
        extra_kwargs = {
            "last_logged_at": {"read_only": True},
            "profile_pic_path": {"read_only": True},
            "profile_pic_url": {"read_only": True},
        }

    def validate(self, attrs):
        # An admin can't change their own role or status — otherwise the
        # last super-admin could demote or deactivate themselves and leave
        # nobody able to use Admin Management. (Only super-admins reach
        # this serializer at all, so another super-admin is always there to
        # make such a change on their behalf.)
        request = self.context.get("request")
        instance = self.instance
        if request is not None and instance is not None and instance.pk == request.user.pk:
            if "type" in attrs and attrs["type"] != instance.type:
                raise serializers.ValidationError({"type": "You cannot change your own admin type."})
            if "status" in attrs and attrs["status"] != instance.status:
                raise serializers.ValidationError({"status": "You cannot change your own status."})
        return super().validate(attrs)


class SellerVerificationLogSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Seller's detail page. Written internally by
    SellerSerializer's create()/update(), never through a client-facing
    field."""

    class Meta:
        model = SellerVerificationLog
        fields = [
            "id", "verification_status", "verification_note",
            "created_by", "creator_type", "creator_name", "created_at",
        ]


class SellerProfileChangeLogSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Seller's detail page for admins. `previous_data`
    and `new_data` have the same keys: only the fields that changed."""

    class Meta:
        model = SellerProfileChangeLog
        fields = [
            "id", "changed_fields", "previous_data", "new_data",
            "created_by", "creator_type", "creator_name", "created_at",
        ]


class SellerListSerializer(serializers.ModelSerializer):
    """List page — basic information only (see AdminListSerializer)."""

    class Meta:
        model = Seller
        fields = [
            "id", "name", "email", "phone", "profile_pic_url",
            "verification_status", "status", "is_seller_request",
            "wallet_balance", "bonus_balance", "last_logged_at", "created_at", "requested_at",
        ]


class SellerSerializer(
    LocationConsistencyMixin, MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin, serializers.ModelSerializer
):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    profile_pic = serializers.ImageField(write_only=True, required=False)
    media = SellerMediaSerializer(many=True, read_only=True)
    media_for = serializers.ListField(
        child=serializers.ChoiceField(choices=SellerMedia.MediaFor.choices),
        write_only=True, required=False, default=list,
    )
    media_file = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, default=list,
    )
    media_delete_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )
    # The seller's business profile — a single nested object (not a list,
    # since it's 1:1), created/replaced through this same call. Written as
    # `info` (a JSON object in a plain JSON request, or a JSON-encoded
    # *string* in a multipart request — multipart has no nested-object
    # syntax, so a string is the only way to carry one alongside a file
    # upload in the same request; JSONField accepts either automatically),
    # and read back as `business_info` — a separate field, because what a
    # client sends (raw, unvalidated JSON) and what the detail page shows
    # (the full validated SellerInfo row) aren't the same shape.
    info = serializers.JSONField(write_only=True, required=False)
    business_info = SellerInfoSerializer(source="info", read_only=True)
    verification_logs = SellerVerificationLogSerializer(many=True, read_only=True)
    profile_change_logs = SellerProfileChangeLogSerializer(many=True, read_only=True)

    media_model = SellerMedia
    media_fk_name = "seller"

    class Meta:
        model = Seller
        fields = [
            "id", "name", "email", "phone", "password",
            "profile_pic", "profile_pic_path", "profile_pic_url",
            "email_verified_at", "phone_verified_at",
            "verification_status", "verification_note", "is_seller_request",
            "skills", "education", "experience", "interest",
            "present_address", "permanent_address",
            "country", "state", "city", "thana",
            "wallet_balance", "bonus_balance", "status", "last_logged_at", "created_at", "requested_at",
            "media", "media_for", "media_file", "media_delete_ids", "info", "business_info",
            "verification_logs", "profile_change_logs",
        ]
        extra_kwargs = {
            "email_verified_at": {"read_only": True},
            "phone_verified_at": {"read_only": True},
            "is_seller_request": {"read_only": True},
            "wallet_balance": {"read_only": True},
            "bonus_balance": {"read_only": True},
            "last_logged_at": {"read_only": True},
            "created_at": {"read_only": True},
            "requested_at": {"read_only": True},
            "profile_pic_path": {"read_only": True},
            "profile_pic_url": {"read_only": True},
        }

    def validate(self, attrs):
        # Only a real move into "rejected" needs a note; re-sending the
        # unchanged status (e.g. a PUT of the whole form) does not.
        instance = self.instance
        status_changes = "verification_status" in attrs and (
            instance is None or attrs["verification_status"] != instance.verification_status
        )
        if status_changes and attrs["verification_status"] == Seller.VerificationStatus.REJECTED and not attrs.get(
            "verification_note"
        ):
            raise serializers.ValidationError(
                {"verification_note": "A verification note is required when rejecting a seller."}
            )
        return super().validate(attrs)

    def _save_info(self, instance, info_data):
        # `info_data` is raw, client-supplied JSON at this point — still
        # needs real validation (required fields, types) before touching
        # the database, hence routing it back through SellerInfoSerializer
        # rather than trusting it directly.
        info_serializer = SellerInfoSerializer(data=info_data)
        info_serializer.is_valid(raise_exception=True)
        SellerInfo.objects.update_or_create(seller=instance, defaults=info_serializer.validated_data)

    def create(self, validated_data):
        info_data = validated_data.pop("info", None)
        # Verified by default when an Admin creates the Seller directly;
        # unverified by default otherwise (e.g. a future self-registration
        # flow) — matches the model's own default, restated here so an
        # Admin who explicitly picks a status in the create payload isn't
        # overridden by it.
        if "verification_status" not in validated_data:
            validated_data["verification_status"] = (
                Seller.VerificationStatus.VERIFIED
                if validated_data.get("creator_type") == ActorType.ADMIN
                else Seller.VerificationStatus.UNVERIFIED
            )
        # verification_note never carries over from anywhere — a Seller
        # doesn't exist yet, so there's nothing to carry over from, but
        # this keeps create and update symmetric: whatever was (or wasn't)
        # provided for this event is exactly what ends up on the row.
        validated_data["verification_note"] = validated_data.get("verification_note") or None
        instance = super().create(validated_data)
        if info_data:
            self._save_info(instance, info_data)
        SellerVerificationLog.objects.create(
            seller=instance,
            verification_status=instance.verification_status,
            verification_note=instance.verification_note,
            created_by=validated_data.get("created_by"),
            creator_type=validated_data.get("creator_type", ActorType.SYSTEM),
            creator_name=validated_data.get("creator_name"),
        )
        return instance

    def update(self, instance, validated_data):
        info_data = validated_data.pop("info", None)
        before = snapshot(instance)
        status_changing = (
            "verification_status" in validated_data
            and validated_data["verification_status"] != instance.verification_status
        )
        account_status_changing = "status" in validated_data and validated_data["status"] != instance.status
        if instance.is_seller_request and (status_changing or account_status_changing):
            # The admin has acted on the registration — it leaves the
            # "Seller Request" queue. Editing anything else keeps it there.
            validated_data["is_seller_request"] = False
        if status_changing:
            # The seller row always holds the note for its *current*
            # status only — never a leftover from a previous status
            # change. So a status-changing update always sets it, to
            # whatever was provided this time or to null if it wasn't.
            validated_data["verification_note"] = validated_data.get("verification_note") or None
        else:
            # A note is the reason for a status change. With no change there
            # is nothing to attach it to, so it is ignored — otherwise the
            # row's note could drift from the latest history entry.
            validated_data.pop("verification_note", None)
        instance = super().update(instance, validated_data)
        if info_data:
            self._save_info(instance, info_data)
        record_profile_changes(
            instance, before,
            validated_data.get("updated_by"), validated_data.get("updater_type", ActorType.SYSTEM),
            validated_data.get("updater_name"),
        )
        if status_changing:
            SellerVerificationLog.objects.create(
                seller=instance,
                verification_status=instance.verification_status,
                verification_note=instance.verification_note,
                created_by=validated_data.get("updated_by"),
                creator_type=validated_data.get("updater_type", ActorType.SYSTEM),
                creator_name=validated_data.get("updater_name"),
            )
        return instance


class BuyerMediaSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Buyer's detail page. Writes happen through
    UserSerializer's media_for/media_file/media_delete_ids instead."""

    class Meta:
        model = BuyerMedia
        fields = ["id", "media_type", "media_for", "media_path", "media_url"]


class BuyerListSerializer(serializers.ModelSerializer):
    """List page — basic information only (see AdminListSerializer)."""

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "profile_pic_url", "wallet_balance", "status"]


class UserSerializer(
    OptionalBuyerEmailMixin, LocationConsistencyMixin, MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin,
    serializers.ModelSerializer,
):
    """Buyer serializer — model is named `User` (see models.py docstring),
    not Django's own auth user."""

    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    profile_pic = serializers.ImageField(write_only=True, required=False)
    media = BuyerMediaSerializer(many=True, read_only=True)
    media_for = serializers.ListField(
        child=serializers.ChoiceField(choices=BuyerMedia.MediaFor.choices),
        write_only=True, required=False, default=list,
    )
    media_file = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, default=list,
    )
    media_delete_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )

    media_model = BuyerMedia
    media_fk_name = "buyer"

    class Meta:
        model = User
        fields = [
            "id", "name", "email", "phone", "password",
            "profile_pic", "profile_pic_path", "profile_pic_url", "description",
            "skills", "experiences", "interests", "educations",
            "email_verified_at", "phone_verified_at",
            "address_line", "country", "state", "city", "thana",
            "wallet_balance", "status",
            "media", "media_for", "media_file", "media_delete_ids",
        ]
        extra_kwargs = {
            "email_verified_at": {"read_only": True},
            "phone_verified_at": {"read_only": True},
            "wallet_balance": {"read_only": True},
            "profile_pic_path": {"read_only": True},
            "profile_pic_url": {"read_only": True},
        }
