import os

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin
from apps.core.models import ActorType
from config.storage import infer_media_type, save_upload

from . import kinds
from .listing_log import record_listing_changes, snapshot
from .models import (
    Attribute,
    AttributeValue,
    Brand,
    Category,
    Listing,
    ListingInfoChangeLog,
    ListingMedia,
    ListingPriceTier,
    ListingSku,
    ListingSkuVariant,
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


class AttributeValueBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ["id", "name", "name_bn", "is_active"]


class AttributeSerializer(serializers.ModelSerializer):
    """Client sends `name` (and optionally `name_bn`, `description`,
    `description_bn`, `is_active`). The attribute's values are managed through
    /attribute-values/ and only shown here, read-only."""

    values = AttributeValueBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = [
            "id", "name", "name_bn", "description", "description_bn", "is_active", "values",
            "created_by", "creator_name", "creator_type", "created_at", "updated_at",
        ]
        read_only_fields = ["created_by", "creator_name", "creator_type", "created_at", "updated_at"]
        extra_kwargs = {"name": {"validators": []}}

    def validate_name(self, name):
        name = name.strip()
        clash = Attribute.objects.filter(name__iexact=name)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("An attribute with this name already exists.")
        return name


class AttributeValueSerializer(serializers.ModelSerializer):
    """One allowed value of an attribute (Size -> XL). The attribute is chosen
    at creation and cannot be changed afterwards: SKUs already point at the
    value, so moving it to another attribute would change their meaning."""

    attribute_name = serializers.CharField(source="attribute.name", read_only=True)

    class Meta:
        model = AttributeValue
        fields = [
            "id", "attribute", "attribute_name", "name", "name_bn", "description", "description_bn",
            "is_active", "created_by", "creator_name", "creator_type", "created_at", "updated_at",
        ]
        read_only_fields = ["created_by", "creator_name", "creator_type", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        instance = self.instance
        attribute = attrs.get("attribute", getattr(instance, "attribute", None))
        if instance is not None and "attribute" in attrs and attrs["attribute"].pk != instance.attribute_id:
            raise serializers.ValidationError({"attribute": "The attribute cannot be changed after creation."})
        if instance is None and not attribute.is_active:
            raise serializers.ValidationError({"attribute": "This attribute is inactive."})
        if "name" in attrs:
            attrs["name"] = attrs["name"].strip()
        name = attrs.get("name", getattr(instance, "name", None))
        clash = AttributeValue.objects.filter(attribute=attribute, name__iexact=name)
        if instance is not None:
            clash = clash.exclude(pk=instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"name": "This attribute already has a value with this name."})
        return attrs


class ListingStatusChangeLogSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Listing's detail page. Written internally by
    ListingSerializer's create()/update(), never through a client-facing
    field."""

    class Meta:
        model = ListingStatusChangeLog
        fields = ["id", "status", "note", "created_by", "creator_type", "creator_name", "created_at"]


class ListingInfoChangeLogSerializer(serializers.ModelSerializer):
    """Read-only — shown on a Listing's detail page for admins. `previous_data`
    and `new_data` have the same keys: only what changed."""

    class Meta:
        model = ListingInfoChangeLog
        fields = [
            "id", "changed_fields", "previous_data", "new_data",
            "created_by", "creator_type", "creator_name", "created_at",
        ]


def _is_empty(value):
    """True for "nothing was sent": None, False, "", [] and {}. (Not `0`: a zero
    is a real value, and `0 == False` would otherwise let it through.)"""
    return value is None or value is False or (isinstance(value, (str, list, dict)) and not value)


def _check_discount(price, discounted_price):
    if price is not None and discounted_price is not None and discounted_price > price:
        raise serializers.ValidationError(
            {"discounted_price": "Cannot be higher than price (price is the original price)."}
        )


class ListingPriceTierSerializer(serializers.ModelSerializer):
    listing_sku = serializers.PrimaryKeyRelatedField(
        queryset=ListingSku.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ListingPriceTier
        fields = ["id", "listing_sku", "min_qty", "max_qty", "price", "discounted_price"]
        extra_kwargs = {
            "min_qty": {"min_value": 1},
            "max_qty": {"min_value": 1},
            "price": {"min_value": 0},
            "discounted_price": {"required": False, "allow_null": True, "min_value": 0},
        }

    def validate(self, attrs):
        if attrs.get("max_qty") is not None and attrs["max_qty"] < attrs["min_qty"]:
            raise serializers.ValidationError({"max_qty": "Must be equal to or greater than min_qty."})
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


class ListingSkuVariantSerializer(serializers.ModelSerializer):
    """One option of a SKU. Client sends `attribute` and `attribute_value`
    (ids); the names are for display."""

    attribute_name = serializers.CharField(source="attribute.name", read_only=True)
    attribute_value_name = serializers.CharField(source="attribute_value.name", read_only=True)

    class Meta:
        model = ListingSkuVariant
        fields = ["attribute", "attribute_name", "attribute_value", "attribute_value_name"]


class ListingSkuSerializer(serializers.ModelSerializer):
    """One sellable combination of a listing. Sent inside a listing's `skus`
    list: an item with an `id` updates that SKU (only the fields sent change;
    `variants`, when sent, replaces its options), an item without an `id`
    creates a new SKU. SKUs are never deleted — send `"is_active": false` to
    hide one."""

    id = serializers.IntegerField(required=False)
    variants = ListingSkuVariantSerializer(many=True, required=False)
    effective_price = serializers.SerializerMethodField()
    is_discount_active = serializers.SerializerMethodField()

    class Meta:
        model = ListingSku
        fields = [
            "id", "sku", "price", "discounted_price", "discount_start_date", "discount_end_date",
            "effective_price", "is_discount_active", "stock_qty", "reserved_qty", "is_active",
            "price_type", "description", "description_bn", "variants",
        ]
        read_only_fields = ["reserved_qty"]
        extra_kwargs = {
            "sku": {"validators": [], "allow_null": True, "allow_blank": True, "required": False},
            "price": {"required": False, "min_value": 0},
            "discounted_price": {"required": False, "allow_null": True, "min_value": 0},
            "stock_qty": {"min_value": 0},
            "price_type": {"required": False, "allow_null": True},
            "description": {"required": False, "allow_null": True, "allow_blank": True},
            "description_bn": {"required": False, "allow_null": True, "allow_blank": True},
        }

    def get_effective_price(self, obj):
        return str(obj.effective_price())

    def get_is_discount_active(self, obj):
        return obj.effective_price() < obj.price


SKU_SHORTCUT_FIELDS = (
    "price", "discounted_price", "discount_start_date", "discount_end_date", "stock_qty", "sku",
    "price_type",
)  # (A SKU's own `description` / `description_bn` go through `skus`: the listing has fields of the same name.)


def _cheapest_sku(listing):
    """The active SKU with the lowest price right now — what a listing page
    shows as "from ...". For a gig this is the lowest rate; `price_type` says
    what the rate is for (an hour, a day, a week, a month, or a fixed price).
    Uses prefetched SKUs when available."""
    active = [sku for sku in listing.skus.all() if sku.is_active]
    return min(active, key=lambda sku: (sku.effective_price(), sku.price)) if active else None


class ListingFromPriceMixin:
    """Read-only `price` / `discounted_price` on a listing: the original and
    the currently charged price of its cheapest active SKU (null when there is
    none). The real prices live on `skus`."""

    def get_price(self, obj):
        sku = _cheapest_sku(obj)
        return str(sku.price) if sku else None

    def get_discounted_price(self, obj):
        sku = _cheapest_sku(obj)
        return str(sku.effective_price()) if sku else None

    def get_price_type(self, obj):
        sku = _cheapest_sku(obj)
        return sku.price_type if sku else None


class ListingListSerializer(ListingFromPriceMixin, serializers.ModelSerializer):
    """List page — basic information only (see CategoryBriefSerializer)."""

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "catalog_type", "listing_type", "posted_by_role",
            "category", "brand", "seller", "buyer", "price", "discounted_price", "image_url", "status",
            "requested_at", "created_at",
        ]


class GigListSerializer(ListingFromPriceMixin, serializers.ModelSerializer):
    """The gig list: `price` / `discounted_price` / `price_type` are those of the
    package with the lowest rate (see _cheapest_sku)."""

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    price_type = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "seller", "price", "discounted_price",
            "price_type", "image_url", "status", "requested_at", "created_at",
        ]


class ListingSerializer(ListingFromPriceMixin, LocationConsistencyMixin, serializers.ModelSerializer):
    """Full detail/write serializer for a Listing.

    `skus` holds the sellable combinations (price, discount, stock, options).
    On update it merges by id and never deletes (see ListingSkuSerializer).
    On create, a plain `price` (with optional `discounted_price`, discount
    dates, `stock_qty`, `sku`) is a shortcut for one default SKU with no
    options. Read-only `price` / `discounted_price` show the cheapest active
    SKU.

    `price_tiers` is a plain nested list: when the key is present in the
    request, the listing's existing tiers are replaced wholesale with
    whatever list was sent (including an empty list, which clears them);
    omitting the key on a PATCH leaves existing tiers untouched.

    Media works like accounts' MediaSyncMixin (media_file +
    media_delete_ids), except there's no `media_for` purpose tag — a
    Listing's media is a plain gallery, so `media_type` is inferred from each
    uploaded file via infer_media_type().
    """

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    skus = ListingSkuSerializer(many=True, required=False)
    price_tiers = ListingPriceTierSerializer(many=True, required=False)
    media = ListingMediaSerializer(many=True, read_only=True)
    media_file = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False, default=list,
    )
    media_delete_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list,
    )
    status_change_logs = ListingStatusChangeLogSerializer(many=True, read_only=True)
    info_change_logs = ListingInfoChangeLogSerializer(many=True, read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default=None)

    # What the error says when the seller already has a listing with this title.
    duplicate_title_message = "This seller already has a listing with this title. Update that listing instead."

    # Which kind of listing this serializer handles (apps.catalog.kinds): `gig`
    # or `product` fix `catalog_type` / `posted_by_role` themselves; `None` is
    # the admin's listing endpoint, which takes products and (for now) jobs.
    scope = None
    # Fields that belong to another kind of listing and are left out of this
    # serializer's `Meta.fields`; sending one is a 400 (see to_internal_value).
    foreign_fields = ()

    class Meta:
        model = Listing
        fields = [
            "id", "seller", "buyer", "category", "catalog_type", "listing_type", "posted_by_role",
            "title", "title_bn", "slug", "description", "description_bn",
            "image_path", "image_url",
            "brand", "brand_name", "model", "origin", "origin_bn", "warranty", "warranty_bn",
            "price", "discounted_price", "currency", "skus",
            "delivery_days", "urgent",
            "package_includes", "package_includes_bn",
            "available_from", "available_to",
            "min_order_qty", "measurement",
            "condition_note", "condition_note_bn", "attributes",
            "country", "state", "city", "thana",
            "status", "note", "requested_at",
            "price_tiers", "media", "media_file", "media_delete_ids",
            "status_change_logs", "info_change_logs",
            "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "image_path", "image_url", "requested_at", "created_at", "updated_at"]
        extra_kwargs = {
            "delivery_days": {"min_value": 0},
            "min_order_qty": {"min_value": 1},
        }

    # ---- input: the create-time price shortcut --------------------------------

    def to_internal_value(self, data):
        # Fields of another kind are not part of this serializer at all (a gig has
        # no brand), so DRF would drop them silently: refuse them instead.
        errors = {
            field: "Not available here."
            for field in self.foreign_fields
            if field in data and not _is_empty(data.get(field))
        }
        if errors:
            raise serializers.ValidationError(errors)
        shortcut = {key: data[key] for key in SKU_SHORTCUT_FIELDS if key in data}
        validated = super().to_internal_value(data)
        if shortcut:
            if self.instance is not None:
                raise serializers.ValidationError(
                    {key: "Prices and stock are changed through `skus`." for key in shortcut}
                )
            if "skus" in validated:
                raise serializers.ValidationError({"skus": "Send either `skus` or the price shortcut, not both."})
            item = ListingSkuSerializer(data=shortcut)
            item.is_valid(raise_exception=True)
            validated["skus"] = [item.validated_data]
        return validated

    # ---- validation -------------------------------------------------------------

    def validate_title(self, value):
        # One space between words, nothing at the ends: "Blue  Tee " and "blue tee" are the same title.
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_price_tiers(self, tiers):
        # Quantity ranges must not overlap: once sorted by min_qty, each
        # tier has to start after the previous one ends, and only the last
        # tier may be open-ended (no max_qty).
        ordered = sorted(tiers, key=lambda tier: tier["min_qty"])
        for previous, current in zip(ordered, ordered[1:]):
            if previous.get("max_qty") is None or current["min_qty"] <= previous["max_qty"]:
                raise serializers.ValidationError(
                    "Price tier quantity ranges must not overlap, and only the last tier can have no max_qty."
                )
        own_sku_ids = set(self.instance.skus.values_list("id", flat=True)) if self.instance is not None else set()
        for tier in tiers:
            sku = tier.get("listing_sku")
            if sku is not None and sku.id not in own_sku_ids:
                raise serializers.ValidationError("A tier's listing_sku must be a SKU of this listing.")
        return tiers

    def _validate_skus(self, skus):
        """Merges each item with the SKU it updates, checks it, and checks the
        listing's whole final set of SKUs together. Returns the items with
        their merged values filled in (`_existing` points at the SKU row)."""
        instance = self.instance
        existing = {sku.id: sku for sku in instance.skus.all()} if instance is not None else {}
        errors = {}
        merged = []
        seen_ids = set()
        codes_in_request = set()

        for index, item in enumerate(skus):
            item_errors = {}
            sku_id = item.get("id")
            current = None
            if sku_id is not None:
                current = existing.get(sku_id)
                if current is None:
                    item_errors["id"] = "This SKU does not belong to this listing."
                elif sku_id in seen_ids:
                    item_errors["id"] = "The same SKU appears twice."
                seen_ids.add(sku_id)
            elif "price" not in item:
                item_errors["price"] = "This field is required for a new SKU."

            price = item.get("price", getattr(current, "price", None))
            if "discounted_price" in item:
                discounted = item["discounted_price"]
            elif current is not None and "price" in item and current.discounted_price == current.price:
                discounted = None  # no discount before -> follows the new price
            else:
                discounted = getattr(current, "discounted_price", None)
            if discounted is None:
                discounted = price
            if price is not None and discounted is not None and discounted > price:
                item_errors["discounted_price"] = "Cannot be higher than price (price is the original price)."
            start = item["discount_start_date"] if "discount_start_date" in item else getattr(current, "discount_start_date", None)
            end = item["discount_end_date"] if "discount_end_date" in item else getattr(current, "discount_end_date", None)
            if start and end and end <= start:
                item_errors["discount_end_date"] = "Must be after discount_start_date."
            if (start or end) and price is not None and discounted == price:
                item_errors["discounted_price"] = "A discount period needs a discounted_price lower than price."

            code = item.get("sku") if "sku" in item else getattr(current, "sku", None)
            if "sku" in item and not code:
                item["sku"] = None
                code = None
            if code:
                clash = ListingSku.objects.filter(sku=code)
                if current is not None:
                    clash = clash.exclude(pk=current.pk)
                if clash.exists():
                    item_errors["sku"] = "A SKU with this code already exists."
                elif code in codes_in_request:
                    item_errors["sku"] = "This SKU code is used twice in this request."
                codes_in_request.add(code)

            if "variants" in item:
                variants = item["variants"]
            elif current is not None:
                variants = [
                    {"attribute": v.attribute, "attribute_value": v.attribute_value} for v in current.variants.all()
                ]
            else:
                variants = []
            previous_values = {v.attribute_id: v.attribute_value_id for v in current.variants.all()} if current else {}
            used_attributes = set()
            for variant in variants:
                attribute, value = variant["attribute"], variant["attribute_value"]
                if attribute.id in used_attributes:
                    item_errors["variants"] = "A SKU can have only one value per attribute."
                    break
                used_attributes.add(attribute.id)
                if value.attribute_id != attribute.id:
                    item_errors["variants"] = f"'{value.name}' is not a value of the attribute '{attribute.name}'."
                    break
                if previous_values.get(attribute.id) != value.id and not (attribute.is_active and value.is_active):
                    item_errors["variants"] = f"'{attribute.name}: {value.name}' is inactive."
                    break

            price_type = item["price_type"] if "price_type" in item else getattr(current, "price_type", None)
            kind = self._kind
            if kind == kinds.PRODUCT:
                for field in kinds.GIG_SKU_FIELDS:
                    if item.get(field) not in (None, ""):
                        item_errors[field] = "Only for gigs."
            else:
                if kind == kinds.GIG:
                    if price_type is None:
                        item_errors["price_type"] = "This field is required for a gig SKU."
                    if item.get("stock_qty") is not None:
                        item_errors["stock_qty"] = "A gig has no stock."
                    if variants:
                        item_errors["variants"] = "A gig SKU has no options."
                else:
                    for field in ("description", "description_bn"):
                        if item.get(field) not in (None, ""):
                            item_errors[field] = "Only for gigs."

            if item_errors:
                errors[index] = item_errors
            merged.append({
                **item, "_existing": current, "_variants": variants, "_price": price, "_discounted": discounted,
                "_price_type": price_type,
            })

        if errors:
            raise serializers.ValidationError({"skus": errors})

        # The listing's final set of SKUs: the ones in this request plus the
        # existing ones it does not mention.
        final = []
        for entry in merged:
            final.append(entry["_variants"])
        for sku_id, sku in existing.items():
            if sku_id not in seen_ids:
                final.append([{"attribute": v.attribute, "attribute_value": v.attribute_value} for v in sku.variants.all()])
        if self._kind != kinds.PRODUCT:
            # A listing has at most one SKU per price type (a database rule too): for a gig
            # this is how it is priced (hourly, daily, ...); a job may set one on its budget SKU.
            types = [entry["_price_type"] for entry in merged if entry["_price_type"]]
            types += [sku.price_type for sku_id, sku in existing.items() if sku_id not in seen_ids and sku.price_type]
            if len(set(types)) != len(types):
                who = "gig SKU" if self._kind == kinds.GIG else "SKU of a job request"
                raise serializers.ValidationError(
                    {"skus": f"Every {who} needs its own price type (two SKUs have the same one)."}
                )
        if self._kind == kinds.GIG:
            return merged  # a gig has no options: nothing else to compare
        combos = [frozenset((v["attribute"].id, v["attribute_value"].id) for v in variants) for variants in final]
        if len(set(combos)) != len(combos):
            raise serializers.ValidationError(
                {"skus": "Every SKU of a listing needs its own combination of options (two SKUs have the same one)."}
            )
        attribute_sets = {frozenset(attribute_id for attribute_id, _ in combo) for combo in combos}
        if len(attribute_sets) > 1:
            raise serializers.ValidationError(
                {"skus": "All SKUs of a listing must use the same attributes (e.g. all Size + Colour)."}
            )
        return merged

    def _apply_scope(self, attrs):
        """Fixes (or checks) which kind of listing this is, rejects the fields
        that belong to another kind, and remembers the kind for the SKU checks."""
        instance = self.instance
        forced = {}
        if self.scope == kinds.GIG:
            forced = {
                "catalog_type": Listing.CatalogType.SERVICE,
                "posted_by_role": Listing.PostedByRole.SELLER_OFFER,
            }
        elif self.scope == kinds.PRODUCT:
            forced = {"catalog_type": Listing.CatalogType.PRODUCT}
        for field, value in forced.items():
            if field in attrs and attrs[field] != value:
                raise serializers.ValidationError(
                    {field: f"This endpoint only handles {self.scope}s: this field must be '{value}'."}
                )
            attrs[field] = value
        if instance is not None:
            for field in ("catalog_type", "posted_by_role"):
                if field in attrs and attrs[field] != getattr(instance, field):
                    raise serializers.ValidationError({field: "Cannot be changed after the listing is created."})

        catalog_type = attrs.get("catalog_type", getattr(instance, "catalog_type", None))
        role = attrs.get("posted_by_role", getattr(instance, "posted_by_role", None))
        if catalog_type == Listing.CatalogType.PRODUCT:
            if role == Listing.PostedByRole.BUYER_REQUEST:
                raise serializers.ValidationError({"posted_by_role": "A product cannot be a buyer_request."})
            kind = kinds.PRODUCT
        elif role == Listing.PostedByRole.BUYER_REQUEST:
            kind = kinds.JOB
        else:
            kind = kinds.GIG
        if self.scope is None and kind == kinds.GIG:
            raise serializers.ValidationError(
                {"catalog_type": "A seller's service offer is a gig: use the gig endpoints (/catalog/gigs/). "
                                 "This endpoint handles products and buyer requests."}
            )
        self._kind = kind

        # Fields of another kind are refused (an empty value is fine).
        errors = {}
        if kind == kinds.PRODUCT:
            forbidden, message = kinds.SERVICE_ONLY_FIELDS, "Only for gigs and job requests."
        else:
            forbidden, message = kinds.PRODUCT_ONLY_FIELDS, f"Not available for a {'gig' if kind == kinds.GIG else 'job request'}."
        for field in forbidden:
            if field in attrs and not _is_empty(attrs[field]):
                errors[field] = message
        if kind != kinds.PRODUCT and attrs.get("price_tiers"):
            errors["price_tiers"] = message
        if errors:
            raise serializers.ValidationError(errors)

    def validate(self, attrs):
        instance = self.instance
        self._check_location(attrs)
        self._apply_scope(attrs)
        if "skus" in attrs:
            attrs["skus"] = self._validate_skus(attrs["skus"])
        if instance is None and not attrs.get("skus"):
            raise serializers.ValidationError(
                {"skus": "A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."}
            )
        # Only fires when THIS request actually moves the listing into
        # rejected/changes_requested — falling back to the instance's
        # current status here would wrongly demand a note on every later,
        # unrelated update to an already-rejected listing, and re-sending
        # the unchanged status (e.g. a PUT of the whole form) is not a
        # status change, so it needs no note either.
        status_changes = "status" in attrs and (instance is None or attrs["status"] != instance.status)
        if status_changes and attrs["status"] in (
            Listing.Status.REJECTED, Listing.Status.CHANGES_REQUESTED
        ) and not attrs.get("note"):
            raise serializers.ValidationError(
                {"note": "A note is required when rejecting a listing or requesting changes."}
            )

        # The category must be of the listing's catalog type (a service
        # category can't hold a product), and a listing can only be put into
        # an active category — checked when either is being set, and the
        # active check only for a category newly chosen, so an already-
        # attached category deactivated later doesn't block other edits.
        category = attrs["category"] if "category" in attrs else getattr(instance, "category", None)
        catalog_type = attrs.get("catalog_type", getattr(instance, "catalog_type", None))
        if category is not None and ("category" in attrs or "catalog_type" in attrs):
            if category.type != catalog_type:
                raise serializers.ValidationError(
                    {"category": f"This is a {category.type} category; a {catalog_type} listing needs a {catalog_type} category."}
                )
        if "category" in attrs and category is not None and getattr(instance, "category_id", None) != category.id:
            if category.status != Category.Status.ACTIVE:
                raise serializers.ValidationError({"category": "This category is inactive."})

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

        # A seller cannot have two live listings with the same title (ignoring
        # case): they update the existing one instead. Checked when the title or
        # the owner is being set.
        title = attrs["title"] if "title" in attrs else getattr(instance, "title", None)
        if seller is not None and title and ("title" in attrs or "seller" in attrs):
            clash = Listing.objects.filter(
                seller=seller, title__iexact=title,
                catalog_type=attrs.get("catalog_type", getattr(instance, "catalog_type", None)),
            )
            if instance is not None:
                clash = clash.exclude(pk=instance.pk)
            existing = clash.values_list("id", flat=True).first()
            if existing is not None:
                raise serializers.ValidationError(
                    {"title": [f"{self.duplicate_title_message} (listing #{existing})"]}
                )

        listing_type = attrs.get("listing_type", getattr(instance, "listing_type", None))
        brand = attrs["brand"] if "brand" in attrs else getattr(instance, "brand", None)
        if listing_type == Listing.ListingType.BRAND and brand is None:
            raise serializers.ValidationError({"brand": "A brand listing must select a brand."})
        # Only a brand being newly picked has to be active — an already-
        # attached brand that was deactivated later shouldn't block edits.
        if "brand" in attrs and brand is not None and not brand.is_active:
            if getattr(instance, "brand_id", None) != brand.id:
                raise serializers.ValidationError({"brand": "This brand is inactive."})
        return attrs

    # ---- writing ------------------------------------------------------------------

    def _generate_slug(self, title):
        base = slugify(title) or "listing"  # a title with no Latin letters (e.g. only Bangla) still gets a slug
        slug = base
        suffix = 1
        while Listing.all_objects.filter(slug=slug).exists():
            suffix += 1
            slug = f"{base}-{suffix}"
        return slug

    def _integrity_error(self, error):
        """A database uniqueness error as a field error the client can show
        (None when it is not one we know, so the caller re-raises it)."""
        constraint = getattr(getattr(getattr(error, "__cause__", None), "diag", None), "constraint_name", "") or ""
        if constraint == "unique_listing_title_per_seller":
            return serializers.ValidationError({"title": [self.duplicate_title_message]})
        if constraint == "unique_sku_price_type_per_listing":
            return serializers.ValidationError(
                {"skus": ["Every SKU needs its own price type (two SKUs have the same one)."]}
            )
        if "sku" in constraint.lower():
            return serializers.ValidationError({"skus": ["A SKU code is already in use."]})
        if "slug" in constraint.lower():
            return serializers.ValidationError(
                {"title": ["Another listing with a similar title was saved at the same moment. Please save again."]}
            )
        return None

    def _save_price_tiers(self, instance, tiers_data):
        instance.price_tiers.all().delete()
        for tier_data in tiers_data:
            ListingPriceTier.objects.create(listing=instance, **tier_data)

    def _save_skus(self, instance, skus_data, stamp):
        for entry in skus_data:
            variants = entry["_variants"]
            fields = {
                key: entry[key]
                for key in ("sku", "price", "discounted_price", "discount_start_date", "discount_end_date",
                            "stock_qty", "is_active", "price_type", "description", "description_bn")
                if key in entry
            }
            sku = entry["_existing"]
            if sku is None:
                sku = ListingSku.objects.create(listing=instance, **fields, **stamp["create"])
                replace_variants = True
            else:
                if "price" in fields and "discounted_price" not in fields and sku.discounted_price == sku.price:
                    fields["discounted_price"] = None  # no discount before -> follows the new price
                for key, value in fields.items():
                    setattr(sku, key, value)
                for key, value in stamp["update"].items():
                    setattr(sku, key, value)
                sku.save()
                replace_variants = "variants" in entry
            if replace_variants:
                sku.variants.all().delete()
                for variant in variants:
                    ListingSkuVariant.objects.create(
                        listing_sku=sku, attribute=variant["attribute"],
                        attribute_value=variant["attribute_value"], **stamp["create"],
                    )

    def _create_media(self, instance, media_file_list):
        for uploaded_file in media_file_list:
            path, url = save_upload(uploaded_file, "listing", str(instance.id))
            ListingMedia.objects.create(
                listing=instance,
                media_type=infer_media_type(uploaded_file),
                media_path=path,
                media_url=url,
            )

    @transaction.atomic
    def create(self, validated_data):
        skus_data = validated_data.pop("skus")
        tiers_data = validated_data.pop("price_tiers", None)
        media_file_list = validated_data.pop("media_file", [])
        validated_data.pop("media_delete_ids", None)  # nothing to delete yet on create
        stamp = {
            "create": {
                "created_by": validated_data.get("created_by"),
                "creator_type": validated_data.get("creator_type", ActorType.SYSTEM),
                "creator_name": validated_data.get("creator_name"),
            },
            "update": {},
        }

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
        if validated_data["status"] == Listing.Status.PENDING:
            validated_data["requested_at"] = timezone.now()

        try:
            instance = super().create(validated_data)
        except IntegrityError as error:
            # Two requests raced past the checks above; a database rule caught the second one.
            raise self._integrity_error(error) or error
        try:
            self._save_skus(instance, skus_data, stamp)
        except IntegrityError as error:
            raise self._integrity_error(error) or error
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

    @transaction.atomic
    def update(self, instance, validated_data):
        skus_data = validated_data.pop("skus", None)
        tiers_data = validated_data.pop("price_tiers", None)
        media_file_list = validated_data.pop("media_file", [])
        delete_ids = validated_data.pop("media_delete_ids", [])
        stamp = {
            "create": {
                "created_by": validated_data.get("updated_by"),
                "creator_type": validated_data.get("updater_type", ActorType.SYSTEM),
                "creator_name": validated_data.get("updater_name"),
            },
            "update": {
                "updated_by": validated_data.get("updated_by"),
                "updater_type": validated_data.get("updater_type"),
                "updater_name": validated_data.get("updater_name"),
            },
        }

        before = snapshot(instance)
        status_changing = (
            "status" in validated_data and validated_data["status"] != instance.status
        )
        if status_changing and validated_data["status"] == Listing.Status.PENDING:
            validated_data["requested_at"] = timezone.now()  # (re)joins the pending list
        if status_changing:
            # The listing row always holds the note for its *current*
            # status only — never a leftover from a previous status
            # change. So a status-changing update always sets it, to
            # whatever was provided this time or to null if it wasn't.
            validated_data["note"] = validated_data.get("note") or None
        else:
            # A note belongs to a status change (it is that change's
            # reason, and is copied to its history row). With no status
            # change there is nothing to attach it to, so it is ignored —
            # otherwise the row's note could drift from the latest log entry.
            validated_data.pop("note", None)
        if "title" in validated_data and slugify(validated_data["title"]) != slugify(instance.title):
            validated_data["slug"] = self._generate_slug(validated_data["title"])  # not for a case-only rename

        try:
            instance = super().update(instance, validated_data)
        except IntegrityError as error:
            raise self._integrity_error(error) or error

        if skus_data is not None:
            try:
                self._save_skus(instance, skus_data, stamp)
            except IntegrityError as error:
                raise self._integrity_error(error) or error
        if tiers_data is not None:
            self._save_price_tiers(instance, tiers_data)
        if delete_ids:
            instance.media.filter(id__in=delete_ids).delete()
        self._create_media(instance, media_file_list)
        record_listing_changes(
            instance, before,
            validated_data.get("updated_by"), validated_data.get("updater_type", ActorType.SYSTEM),
            validated_data.get("updater_name"),
        )

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


class SellerListingListSerializer(ListingFromPriceMixin, serializers.ModelSerializer):
    """A seller's own product list: what they need to see at a glance."""

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "catalog_type", "listing_type",
            "category", "brand", "price", "discounted_price", "image_url",
            "status", "note", "requested_at", "created_at", "updated_at",
        ]


class SellerGigListSerializer(ListingFromPriceMixin, serializers.ModelSerializer):
    """A seller's own gig list (see GigListSerializer for the price fields)."""

    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    price_type = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "price", "discounted_price", "price_type",
            "image_url", "status", "note", "requested_at", "created_at", "updated_at",
        ]


class SellerStatusLogSerializer(serializers.ModelSerializer):
    """The status history as a seller sees it: what happened, why and when, and
    whether the seller or an admin did it, but not which admin."""

    class Meta:
        model = ListingStatusChangeLog
        fields = ["id", "status", "note", "creator_type", "created_at"]


# Files a seller may attach to a listing: pictures, a short video or a PDF.
LISTING_MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".pdf"}
LISTING_MEDIA_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "application/pdf",
}
LISTING_MEDIA_MAX_BYTES = 10 * 1024 * 1024
LISTING_MEDIA_MAX_PER_REQUEST = 10
LISTING_MEDIA_MAX_PER_LISTING = 20


class SellerListingMixin:
    """What makes a listing serializer a seller's own (`/seller/listings/`,
    `/seller/gigs/`): the moderation parts are taken away from the seller.

    - The owner is always the logged-in seller and the listing is always a
      `seller_offer`: `seller`, `buyer` and `posted_by_role` are not accepted.
    - `status` is read-only. A new listing is always `pending`. Saving a
      `rejected` or `changes_requested` listing sends it back to `pending`
      (and to the admin's pending list as the newest request). Saving an
      `approved` or `pending` listing leaves its status alone.
    - `note` is the admin's reason when the listing was rejected. A note sent
      while saving a rejected / changes-requested listing becomes the seller's
      message to the reviewer; in any other state a note is ignored.
    - The seller sees the status history but not the info change log."""

    duplicate_title_message = "You already have a listing with this title. Update the existing listing instead."

    def validate_media_file(self, files):
        # Sellers upload through a public-facing form, so the files are limited
        # (an admin's uploads are not).
        if len(files) > LISTING_MEDIA_MAX_PER_REQUEST:
            raise serializers.ValidationError(f"Upload at most {LISTING_MEDIA_MAX_PER_REQUEST} files at a time.")
        for uploaded in files:
            extension = os.path.splitext(uploaded.name)[1].lower()
            content_type = (uploaded.content_type or "").lower()
            if extension not in LISTING_MEDIA_EXTENSIONS or content_type not in LISTING_MEDIA_CONTENT_TYPES:
                raise serializers.ValidationError(
                    f"{uploaded.name}: only JPG, PNG, WEBP, GIF, MP4 or PDF files are accepted."
                )
            if uploaded.size > LISTING_MEDIA_MAX_BYTES:
                raise serializers.ValidationError(
                    f"{uploaded.name}: each file must be {LISTING_MEDIA_MAX_BYTES // (1024 * 1024)} MB or smaller."
                )
        return files

    def validate(self, attrs):
        new_files = attrs.get("media_file") or []
        if new_files:
            keeping = 0
            if self.instance is not None:
                keeping = self.instance.media.exclude(id__in=attrs.get("media_delete_ids") or []).count()
            if keeping + len(new_files) > LISTING_MEDIA_MAX_PER_LISTING:
                raise serializers.ValidationError(
                    {"media_file": f"A listing can have at most {LISTING_MEDIA_MAX_PER_LISTING} files."}
                )
        if self.instance is None:
            attrs["seller"] = self.context["request"].user
            attrs["posted_by_role"] = Listing.PostedByRole.SELLER_OFFER
            attrs.pop("note", None)  # a new listing has no reason to explain yet
        return super().validate(attrs)

    def update(self, instance, validated_data):
        # A listing an admin left as a draft is submitted the same way.
        if instance.status in Listing.RESUBMIT_STATUSES:
            validated_data["status"] = Listing.Status.PENDING
            validated_data["note"] = validated_data.get("note") or None
        else:
            validated_data.pop("note", None)
        return super().update(instance, validated_data)


_SELLER_HIDDEN_FIELDS = ("seller", "buyer", "posted_by_role", "info_change_logs")


class SellerListingSerializer(SellerListingMixin, ListingSerializer):
    """A seller's own product (`/seller/listings/`). Service fields are not
    part of a product; a seller's service offer is a gig (SellerGigSerializer)."""

    scope = kinds.PRODUCT
    foreign_fields = kinds.SERVICE_ONLY_FIELDS
    status_change_logs = SellerStatusLogSerializer(many=True, read_only=True)

    class Meta(ListingSerializer.Meta):
        fields = [
            name for name in ListingSerializer.Meta.fields
            if name not in _SELLER_HIDDEN_FIELDS and name not in kinds.SERVICE_ONLY_FIELDS
        ]
        read_only_fields = ListingSerializer.Meta.read_only_fields + ["status"]
        extra_kwargs = {**ListingSerializer.Meta.extra_kwargs, "catalog_type": {"required": False}}


_GIG_HIDDEN_FIELDS = kinds.PRODUCT_ONLY_FIELDS + ("brand_name", "price_tiers", "buyer")


class GigSerializer(ListingSerializer):
    """The admin's gig (`/catalog/gigs/`): a seller's service offer. It is priced
    by its SKUs, one per price type (hourly, daily, weekly, monthly, fixed); the
    buyer chooses the duration when ordering. It has no options, stock, brand or quantity prices. The
    owner (`seller`) is optional for an admin."""

    scope = kinds.GIG
    foreign_fields = kinds.PRODUCT_ONLY_FIELDS + ("price_tiers",)

    class Meta(ListingSerializer.Meta):
        fields = [name for name in ListingSerializer.Meta.fields if name not in _GIG_HIDDEN_FIELDS]
        extra_kwargs = {
            **ListingSerializer.Meta.extra_kwargs,
            "catalog_type": {"required": False},
            "posted_by_role": {"required": False},
        }


class SellerGigSerializer(SellerListingMixin, GigSerializer):
    """A seller's own gig (`/seller/gigs/`)."""

    status_change_logs = SellerStatusLogSerializer(many=True, read_only=True)

    class Meta(GigSerializer.Meta):
        fields = [name for name in GigSerializer.Meta.fields if name not in _SELLER_HIDDEN_FIELDS]
        read_only_fields = GigSerializer.Meta.read_only_fields + ["status"]
