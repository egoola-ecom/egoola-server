import re

from rest_framework import serializers

from apps.catalog.models import Category
from config.storage import delete_upload, save_upload

from .models import Banner, EmailTemplate, Setting

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
KEY_MESSAGE = "Use lowercase letters, digits and underscores only, starting with a letter."

# Written only by the site-logo endpoint (see SiteLogoView) — the generic
# settings API shows them but never lets a client create, change or delete them.
LOGO_PATH_KEY = "site_logo_path"
LOGO_URL_KEY = "site_logo_url"
RESERVED_SETTING_KEYS = {LOGO_PATH_KEY, LOGO_URL_KEY}


class BannerSerializer(serializers.ModelSerializer):
    """Client sends `placement` and an `image` file (required on create,
    optional on update — sending one replaces the old file); `image_path` /
    `image_url` are always server-computed. `category` is for sidebar
    banners only."""

    image = serializers.ImageField(write_only=True, required=False)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Banner
        fields = [
            "id", "placement", "heading", "small_heading", "link_url",
            "image", "image_path", "image_url", "category",
            "status", "sort_order", "starts_at", "ends_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["image_path", "image_url", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        placement = attrs.get("placement", getattr(instance, "placement", None))
        category = attrs["category"] if "category" in attrs else getattr(instance, "category", None)
        if category is not None and placement != Banner.Placement.SIDEBAR:
            raise serializers.ValidationError(
                {"category": "A category can only be set on a sidebar banner (clear it when changing the placement)."}
            )
        starts_at = attrs["starts_at"] if "starts_at" in attrs else getattr(instance, "starts_at", None)
        ends_at = attrs["ends_at"] if "ends_at" in attrs else getattr(instance, "ends_at", None)
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "Must be after starts_at."})
        if instance is None and "image" not in attrs:
            raise serializers.ValidationError({"image": "A banner needs an image."})
        return attrs

    def _apply_image(self, instance, image):
        old_path = instance.image_path
        instance.image_path, instance.image_url = save_upload(image, "banners")
        instance.save(update_fields=["image_path", "image_url"])
        if old_path and old_path != instance.image_path:
            delete_upload(old_path)

    def create(self, validated_data):
        image = validated_data.pop("image")
        instance = super().create(validated_data)
        self._apply_image(instance, image)
        return instance

    def update(self, instance, validated_data):
        image = validated_data.pop("image", None)
        instance = super().update(instance, validated_data)
        if image is not None:
            self._apply_image(instance, image)
        return instance


class EmailTemplateSerializer(serializers.ModelSerializer):
    """`key` is the stable id application code looks the template up by —
    lowercase snake_case, set once at creation and never changed after."""

    class Meta:
        model = EmailTemplate
        fields = ["id", "key", "subject", "content", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"key": {"validators": []}}

    def validate_key(self, key):
        if not KEY_PATTERN.match(key):
            raise serializers.ValidationError(KEY_MESSAGE)
        if self.instance is not None:
            if key != self.instance.key:
                raise serializers.ValidationError("The key cannot be changed after creation.")
            return key
        if EmailTemplate.objects.filter(key=key).exists():
            raise serializers.ValidationError("A template with this key already exists.")
        return key


class SettingSerializer(serializers.ModelSerializer):
    """Generic key -> JSON value. `key` is set at creation and never
    changed; `value` can be any JSON (number, string, bool, list, object).
    The two site-logo keys are read-only here — see SiteLogoView."""

    value = serializers.JSONField()

    class Meta:
        model = Setting
        fields = ["key", "value", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"key": {"validators": []}}

    def validate_key(self, key):
        if not KEY_PATTERN.match(key):
            raise serializers.ValidationError(KEY_MESSAGE)
        if self.instance is not None:
            if key != self.instance.key:
                raise serializers.ValidationError("The key cannot be changed after creation.")
            return key
        if key in RESERVED_SETTING_KEYS:
            raise serializers.ValidationError("This key is managed by the site-logo endpoint.")
        if Setting.objects.filter(key=key).exists():
            raise serializers.ValidationError("A setting with this key already exists.")
        return key

    def validate(self, attrs):
        if self.instance is not None and self.instance.key in RESERVED_SETTING_KEYS:
            raise serializers.ValidationError(
                {"key": "This setting is managed by the site-logo endpoint and cannot be edited here."}
            )
        return attrs


class SiteLogoUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
