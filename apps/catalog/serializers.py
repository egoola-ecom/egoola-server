from django.utils.text import slugify
from rest_framework import serializers

from config.storage import save_upload

from .models import Category, Measurement


class CategorySerializer(serializers.ModelSerializer):
    """Client sends `type`, `name`, and optionally `parent`/`image`/
    `sort_order`/`status` — slug is always server-generated from `name`
    (see validate()/create()/update()). `image` is write-only: the actual
    upload lands in image_path/image_url, which stay read-only from the
    client's point of view.

    `parent` is a plain, nullable self-FK: pass an id to attach/move under
    another category, omit it to leave the current parent alone (PATCH),
    or pass `null` explicitly to detach it. validate() enforces same-type
    parents and rejects any change that would create a cycle (see there
    for the full reasoning)."""

    image = serializers.ImageField(write_only=True, required=False)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Category
        fields = [
            "id", "type", "name", "slug", "parent",
            "image", "image_path", "image_url",
            "sort_order", "status",
        ]
        read_only_fields = ["slug", "image_path", "image_url"]

    def validate(self, attrs):
        instance = self.instance
        name = attrs.get("name", getattr(instance, "name", None))
        category_type = attrs.get("type", getattr(instance, "type", None))

        # Duplicate check is scoped to `type` — the same name is fine
        # under a product category and a service category, but not twice
        # within the same type.
        slug = slugify(name)
        clash = Category.objects.filter(type=category_type, slug=slug)
        if instance is not None:
            clash = clash.exclude(pk=instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"name": "A category with this name already exists for this type."}
            )

        # `parent` may be absent from attrs entirely (PATCH didn't touch
        # it — fall back to the current value, so a `type` change alone
        # still gets checked against whatever parent is already attached),
        # explicitly None (detaching), or a Category instance.
        parent = attrs["parent"] if "parent" in attrs else getattr(instance, "parent", None)

        if parent is not None:
            if parent.type != category_type:
                raise serializers.ValidationError(
                    {"parent": "Parent category must be the same type as this category."}
                )
            if instance is not None:
                # Walk parent's own ancestor chain — if it ever reaches
                # this instance, attaching `parent` would close a loop
                # (this instance would become its own, possibly indirect,
                # ancestor). Covers both "B can't be A's parent when A is
                # already B's parent" and any deeper nested case.
                node = parent
                while node is not None:
                    if node.pk == instance.pk:
                        raise serializers.ValidationError(
                            {"parent": "This parent would create a circular category chain."}
                        )
                    node = node.parent

        return attrs

    def _apply_image(self, instance, image):
        path, url = save_upload(image, "categories")
        instance.image_path = path
        instance.image_url = url
        instance.save(update_fields=["image_path", "image_url"])

    def create(self, validated_data):
        image = validated_data.pop("image", None)
        validated_data["slug"] = slugify(validated_data["name"])
        instance = super().create(validated_data)
        if image is not None:
            self._apply_image(instance, image)
        return instance

    def update(self, instance, validated_data):
        image = validated_data.pop("image", None)
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        instance = super().update(instance, validated_data)
        if image is not None:
            self._apply_image(instance, image)
        return instance


class MeasurementSerializer(serializers.ModelSerializer):
    """Client sends `name` and `symbol` — `slug` is always server-generated
    from `name`, and duplicate names are rejected via a global slug clash
    check (there's no scoping dimension here, unlike Category's per-type
    check)."""

    class Meta:
        model = Measurement
        fields = ["id", "name", "slug", "symbol"]
        read_only_fields = ["slug"]

    def validate_name(self, name):
        slug = slugify(name)
        clash = Measurement.objects.filter(slug=slug)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A measurement with this name already exists.")
        return name

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)
