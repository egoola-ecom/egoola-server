from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.core.models import ActorType
from config.storage import infer_media_type, save_upload

from .models import Admin, AdminMedia, BuyerMedia, Seller, SellerInfo, SellerMedia, SellerVerificationLog, User


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
        instance.profile_pic_path = path
        instance.profile_pic_url = url
        instance.save(update_fields=["profile_pic_path", "profile_pic_url"])

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


class AdminSerializer(MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin, serializers.ModelSerializer):
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


class SellerMediaSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Seller's detail page. Writes happen through
    SellerSerializer's media_for/media_file/media_delete_ids instead."""

    class Meta:
        model = SellerMedia
        fields = ["id", "media_type", "media_for", "media_path", "media_url"]


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


class SellerInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerInfo
        fields = [
            "business_type", "main_product", "owner_name",
            "employees_range", "annual_revenue", "established_year", "description",
            "public_email", "whatsapp", "facebook", "wechat", "skype",
            "country", "state", "city", "thana",
        ]


class SellerListSerializer(serializers.ModelSerializer):
    """List page — basic information only (see AdminListSerializer)."""

    class Meta:
        model = Seller
        fields = [
            "id", "name", "email", "phone", "profile_pic_url",
            "verification_status", "status", "wallet_balance", "bonus_balance", "last_logged_at",
        ]


class SellerSerializer(MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin, serializers.ModelSerializer):
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

    media_model = SellerMedia
    media_fk_name = "seller"

    class Meta:
        model = Seller
        fields = [
            "id", "name", "email", "phone", "password",
            "profile_pic", "profile_pic_path", "profile_pic_url",
            "email_verified_at", "phone_verified_at",
            "verification_status", "verification_note",
            "skills", "education", "experience", "interest",
            "present_address", "permanent_address",
            "country", "state", "city", "thana",
            "wallet_balance", "bonus_balance", "status", "last_logged_at",
            "media", "media_for", "media_file", "media_delete_ids", "info", "business_info",
            "verification_logs",
        ]
        extra_kwargs = {
            "email_verified_at": {"read_only": True},
            "phone_verified_at": {"read_only": True},
            "wallet_balance": {"read_only": True},
            "bonus_balance": {"read_only": True},
            "last_logged_at": {"read_only": True},
            "profile_pic_path": {"read_only": True},
            "profile_pic_url": {"read_only": True},
        }

    def validate(self, attrs):
        if attrs.get("verification_status") == Seller.VerificationStatus.REJECTED and not attrs.get(
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
        status_changing = (
            "verification_status" in validated_data
            and validated_data["verification_status"] != instance.verification_status
        )
        if status_changing:
            # The seller row always holds the note for its *current*
            # status only — never a leftover from a previous status
            # change. So a status-changing update always sets it, to
            # whatever was provided this time or to null if it wasn't.
            validated_data["verification_note"] = validated_data.get("verification_note") or None
        instance = super().update(instance, validated_data)
        if info_data:
            self._save_info(instance, info_data)
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


class UserSerializer(MediaSyncMixin, ProfilePicUploadMixin, PasswordWriteMixin, serializers.ModelSerializer):
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
