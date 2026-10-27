"""
Serializers for the buyer's own cart (`/api/v1/buyer/cart/...`). See
buyer_views.py and docs/buyer-api-guide.md.
"""

from rest_framework import serializers

from apps.catalog.models import Listing, ListingSku
from apps.catalog.public_listings import buyer_visible_listings

from .models import Cart, CartItem


def _variant_value(sku, name_fragment):
    """Best-effort text snapshot of one of this SKU's variants (e.g. its
    colour or size), matched by attribute name. `color`/`size` on CartItem
    are a display convenience only — `listing_sku` is the source of truth."""
    for variant in sku.variants.all():
        if name_fragment in variant.attribute.name.lower():
            return variant.attribute_value.name
    return None


def variant_snapshot(sku):
    return {
        "color": _variant_value(sku, "colour") or _variant_value(sku, "color"),
        "size": _variant_value(sku, "size"),
    }


class CartItemListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ["id", "title", "title_bn", "slug", "image_url", "catalog_type"]


class CartItemSkuSerializer(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = ListingSku
        fields = ["id", "sku", "price", "discounted_price", "price_type", "is_active"]

    def get_discounted_price(self, obj):
        return str(obj.effective_price())


class CartItemSerializer(serializers.ModelSerializer):
    listing = CartItemListingSerializer(read_only=True)
    listing_sku = CartItemSkuSerializer(read_only=True)
    unit_price = serializers.SerializerMethodField()
    line_subtotal = serializers.SerializerMethodField()
    available = serializers.BooleanField(source="is_available", read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id", "listing", "listing_sku", "qty", "duration", "color", "size",
            "unit_price", "line_subtotal", "available", "created_at",
        ]

    def get_unit_price(self, obj):
        return str(obj.unit_price) if obj.unit_price is not None else None

    def get_line_subtotal(self, obj):
        return str(obj.line_subtotal) if obj.line_subtotal is not None else None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "cart_type", "is_active", "items", "subtotal", "created_at", "updated_at"]

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class AddCartItemSerializer(serializers.Serializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=buyer_visible_listings())
    listing_sku = serializers.PrimaryKeyRelatedField(queryset=ListingSku.objects.filter(is_active=True))
    qty = serializers.IntegerField(required=False, min_value=1)
    duration = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        listing, sku = attrs["listing"], attrs["listing_sku"]
        if sku.listing_id != listing.id:
            raise serializers.ValidationError({"listing_sku": "Does not belong to this listing."})

        if listing.catalog_type == Listing.CatalogType.PRODUCT:
            if "duration" in attrs:
                raise serializers.ValidationError({"duration": "Not used for a product."})
            if attrs.get("qty") is None:
                raise serializers.ValidationError({"qty": "This field is required."})
            if sku.stock_qty is not None and sku.stock_qty - sku.reserved_qty < attrs["qty"]:
                raise serializers.ValidationError({"qty": "Not enough stock."})
        else:
            if "qty" in attrs:
                raise serializers.ValidationError({"qty": "Not used for a gig."})
            if attrs.get("duration") is None:
                raise serializers.ValidationError({"duration": "This field is required."})
        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    qty = serializers.IntegerField(required=False, min_value=1)
    duration = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        is_product = self.instance.qty is not None
        if is_product:
            if "duration" in attrs:
                raise serializers.ValidationError({"duration": "Not used for a product."})
            if "qty" not in attrs:
                raise serializers.ValidationError({"qty": "This field is required."})
            sku = self.instance.listing_sku
            if sku and sku.stock_qty is not None and sku.stock_qty - sku.reserved_qty < attrs["qty"]:
                raise serializers.ValidationError({"qty": "Not enough stock."})
        else:
            if "qty" in attrs:
                raise serializers.ValidationError({"qty": "Not used for a gig."})
            if "duration" not in attrs:
                raise serializers.ValidationError({"duration": "This field is required."})
        return attrs

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
