from django.utils.text import slugify
from rest_framework import serializers

from apps.core.models import ActorType
from config.storage import infer_media_type, save_upload

from .models import (
    Brand,
    Category,
    Listing,
    ListingMedia,
    ListingPriceTier,
    ListingStatusChangeLog,
    Measurement,
)


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


class CategoryBriefSerializer(serializers.ModelSerializer):
    """Flat, non-recursive view of a category — used for the parent-chain
    API's `parents` entries and the category itself, where the full
    CategorySerializer's `parent` field (and its queryset-backed validation)
    isn't relevant."""

    class Meta:
        model = Category
        fields = ["id", "type", "name", "slug", "image_path", "image_url", "sort_order", "status"]


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


class BrandSerializer(serializers.ModelSerializer):
    """Client sends `name` (and optionally `is_active`) — `slug` is always
    server-generated from `name`, unique across the whole project, so a
    duplicate name is rejected the same way Measurement does it."""

    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "is_active", "created_by", "creator_name", "creator_type"]
        read_only_fields = ["slug", "created_by", "creator_name", "creator_type"]

    def validate_name(self, name):
        clash = Brand.objects.filter(slug=slugify(name))
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A brand with this name already exists.")
        return name

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["slug"] = slugify(validated_data["name"])
        return super().update(instance, validated_data)


class ListingStatusChangeLogSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Listing's detail page. Written internally by
    ListingSerializer's create()/update(), never through a client-facing
    field."""

    class Meta:
        model = ListingStatusChangeLog
        fields = ["id", "status", "note", "created_by", "creator_type", "creator_name", "created_at"]


def _check_discount(price, discounted_price):
    if price is not None and discounted_price is not None and discounted_price > price:
        raise serializers.ValidationError(
            {"discounted_price": "Cannot be higher than price (price is the original price)."}
        )


class ListingPriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPriceTier
        fields = ["id", "min_qty", "max_qty", "price", "discounted_price"]
        extra_kwargs = {"discounted_price": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        # No discount given -> the tier's discounted_price is its price.
        if attrs.get("discounted_price") is None:
            attrs["discounted_price"] = attrs["price"]
        _check_discount(attrs["price"], attrs["discounted_price"])
        return attrs


class ListingMediaSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Listing's detail page. Writes happen through
    ListingSerializer's media_file/media_delete_ids instead."""

    class Meta:
        model = ListingMedia
        fields = ["id", "media_type", "media_path", "media_url"]


class ListingListSerializer(serializers.ModelSerializer):
    """List page — basic information only (see CategoryBriefSerializer)."""

    class Meta:
        model = Listing
        fields = [
            "id", "title", "slug", "catalog_type", "listing_type",
            "category", "brand", "seller", "buyer", "price", "discounted_price", "status", "created_at",
        ]


class ListingSerializer(serializers.ModelSerializer):
    """Full detail/write serializer for a Listing.

    `price_tiers` is a plain nested list: when the key is present in the
    request, the listing's existing tiers are replaced wholesale with
    whatever list was sent (including an empty list, which clears them);
    omitting the key on a PATCH leaves existing tiers untouched — there's
    no per-tier partial-update semantics, same reasoning as accounts'
    media-is-delete-and-reupload-not-edit-in-place approach.

    Media works exactly like accounts' MediaSyncMixin (media_file +
    media_delete_ids), except there's no `media_for` purpose tag to
    collect — a Listing's media is a plain gallery, not NID/certificate/
    profile-pic slots, so `media_type` is inferred straight off each
    uploaded file via infer_media_type() and that's the whole of it.
    """

    price_tiers = ListingPriceTierSerializer(many=True, required=False)
    media = ListingMediaSerializer(many=True, read_only=True)
    media_file = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, default=list,
    )
    media_delete_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )
    status_change_logs = ListingStatusChangeLogSerializer(many=True, read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default=None)

    class Meta:
        model = Listing
        fields = [
            "id", "seller", "buyer", "category", "catalog_type", "listing_type", "posted_by_role",
            "title", "slug", "description",
            "brand", "brand_name", "model", "color", "origin", "warranty",
            "price", "discounted_price", "currency",
            "price_type", "hourly_rate", "delivery_days", "urgent", "package_includes",
            "available_from", "available_to",
            "min_order_qty", "stock_qty", "measurement", "colors", "sizes", "reserved_qty",
            "condition_note", "attributes",
            "country", "state", "city", "thana",
            "status", "note",
            "price_tiers", "media", "media_file", "media_delete_ids", "status_change_logs",
            "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]
        extra_kwargs = {"discounted_price": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        instance = self.instance
        # Only fires when THIS request is the one setting status to
        # rejected/changes_requested — falling back to the instance's
        # current status here would wrongly demand a note on every later,
        # unrelated update to an already-rejected listing.
        if attrs.get("status") in (Listing.Status.REJECTED, Listing.Status.CHANGES_REQUESTED) and not attrs.get(
            "note"
        ):
            raise serializers.ValidationError(
                {"note": "A note is required when rejecting a listing or requesting changes."}
            )

        # seller/buyer are both optional (an Admin can create a listing
        # owned by neither), but a listing never has both, and the one that
        # is set must match posted_by_role.
        posted_by_role = attrs.get("posted_by_role", getattr(instance, "posted_by_role", None))
        seller = attrs["seller"] if "seller" in attrs else getattr(instance, "seller", None)
        buyer = attrs["buyer"] if "buyer" in attrs else getattr(instance, "buyer", None)
        if seller and buyer:
            raise serializers.ValidationError({"buyer": "A listing cannot have both a seller and a buyer."})
        if posted_by_role == Listing.PostedByRole.SELLER_OFFER and buyer:
            raise serializers.ValidationError({"buyer": "A seller_offer listing cannot have a buyer."})
        if posted_by_role == Listing.PostedByRole.BUYER_REQUEST and seller:
            raise serializers.ValidationError({"seller": "A buyer_request listing cannot have a seller."})

        listing_type = attrs.get("listing_type", getattr(instance, "listing_type", None))
        brand = attrs["brand"] if "brand" in attrs else getattr(instance, "brand", None)
        if listing_type == Listing.ListingType.BRAND and brand is None:
            raise serializers.ValidationError({"brand": "A brand listing must select a brand."})
        # Only a brand being newly picked has to be active — an already-
        # attached brand that was deactivated later shouldn't block edits.
        if "brand" in attrs and brand is not None and not brand.is_active:
            if getattr(instance, "brand_id", None) != brand.id:
                raise serializers.ValidationError({"brand": "This brand is inactive."})

        # discounted_price is never empty: no discount means it equals price.
        # On create, or when sent as null, it becomes the price. On update, a
        # listing that had no discount (discounted == price) follows a new
        # price instead of being left behind at the old one.
        price = attrs.get("price", getattr(instance, "price", None))
        if instance is None or "discounted_price" in attrs:
            if attrs.get("discounted_price") is None:
                attrs["discounted_price"] = price
        elif "price" in attrs and instance.discounted_price == instance.price:
            attrs["discounted_price"] = attrs["price"]
        discounted = attrs.get("discounted_price", getattr(instance, "discounted_price", None))
        _check_discount(price, discounted)

        return attrs

    def _generate_slug(self, title):
        base = slugify(title)
        slug = base
        suffix = 1
        while Listing.all_objects.filter(slug=slug).exists():
            suffix += 1
            slug = f"{base}-{suffix}"
        return slug

    def _save_price_tiers(self, instance, tiers_data):
        instance.price_tiers.all().delete()
        for tier_data in tiers_data:
            ListingPriceTier.objects.create(listing=instance, **tier_data)

    def _create_media(self, instance, media_file_list):
        for uploaded_file in media_file_list:
            path, url = save_upload(uploaded_file, "listing", str(instance.id))
            ListingMedia.objects.create(
                listing=instance,
                media_type=infer_media_type(uploaded_file),
                media_path=path,
                media_url=url,
            )

    def create(self, validated_data):
        tiers_data = validated_data.pop("price_tiers", None)
        media_file_list = validated_data.pop("media_file", [])
        validated_data.pop("media_delete_ids", None)  # nothing to delete yet on create

        # Approved by default when an Admin creates the Listing directly;
        # pending by default otherwise (e.g. a future seller self-service
        # create) — matches the model's own default, restated here so an
        # Admin who explicitly picks a status in the create payload isn't
        # overridden by it. Same branch as SellerSerializer.create().
        if "status" not in validated_data:
            validated_data["status"] = (
                Listing.Status.APPROVED
                if validated_data.get("creator_type") == ActorType.ADMIN
                else Listing.Status.PENDING
            )
        # note never carries over from anywhere — a Listing
        # doesn't exist yet, so there's nothing to carry over from, but
        # this keeps create and update symmetric: whatever was (or wasn't)
        # provided for this event is exactly what ends up on the row.
        validated_data["note"] = validated_data.get("note") or None
        validated_data["slug"] = self._generate_slug(validated_data["title"])

        instance = super().create(validated_data)
        if tiers_data is not None:
            self._save_price_tiers(instance, tiers_data)
        self._create_media(instance, media_file_list)

        ListingStatusChangeLog.objects.create(
            listing=instance,
            status=instance.status,
            note=instance.note,
            created_by=validated_data.get("created_by"),
            creator_type=validated_data.get("creator_type", ActorType.SYSTEM),
            creator_name=validated_data.get("creator_name"),
        )
        return instance

    def update(self, instance, validated_data):
        tiers_data = validated_data.pop("price_tiers", None)
        media_file_list = validated_data.pop("media_file", [])
        delete_ids = validated_data.pop("media_delete_ids", [])

        status_changing = (
            "status" in validated_data and validated_data["status"] != instance.status
        )
        if status_changing:
            # The listing row always holds the note for its *current*
            # status only — never a leftover from a previous status
            # change. So a status-changing update always sets it, to
            # whatever was provided this time or to null if it wasn't.
            validated_data["note"] = validated_data.get("note") or None
        if "title" in validated_data and validated_data["title"] != instance.title:
            validated_data["slug"] = self._generate_slug(validated_data["title"])

        instance = super().update(instance, validated_data)

        if tiers_data is not None:
            self._save_price_tiers(instance, tiers_data)
        if delete_ids:
            instance.media.filter(id__in=delete_ids).delete()
        self._create_media(instance, media_file_list)

        if status_changing:
            ListingStatusChangeLog.objects.create(
                listing=instance,
                status=instance.status,
                note=instance.note,
                created_by=validated_data.get("updated_by"),
                creator_type=validated_data.get("updater_type", ActorType.SYSTEM),
                creator_name=validated_data.get("updater_name"),
            )
        return instance
