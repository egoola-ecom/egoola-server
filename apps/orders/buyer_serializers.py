"""
Serializers for the buyer's own cart (`/api/v1/buyer/cart/...`). See
buyer_views.py and docs/buyer-api-guide.md.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.accounts.public_views import public_seller_listings_q
from apps.catalog.models import Listing, ListingSku
from apps.catalog.public_listings import GIG_SCOPE, PRODUCT_SCOPE

from .models import Cart, CartItem


def visible_listings():
    """Listings a buyer may add to their cart: the same visibility rule as
    public browsing (approved, seller verified and active, not a buyer's own
    job request) — nothing a buyer can't already see in the shop."""
    return Listing.objects.filter(
        PRODUCT_SCOPE | GIG_SCOPE, public_seller_listings_q(), status=Listing.Status.APPROVED
    )


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


class _CartItemListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ["id", "title", "title_bn", "slug", "image_url", "catalog_type"]


class _CartItemSkuSerializer(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = ListingSku
        fields = ["id", "sku", "price", "discounted_price", "price_type", "is_active"]

    def get_discounted_price(self, obj):
        return str(obj.effective_price())


class CartItemSerializer(serializers.ModelSerializer):
    listing = _CartItemListingSerializer(read_only=True)
    listing_sku = _CartItemSkuSerializer(read_only=True)
    unit_price = serializers.SerializerMethodField()
    line_subtotal = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id", "listing", "listing_sku", "qty", "duration", "color", "size",
            "unit_price", "line_subtotal", "available", "created_at",
        ]

    def _units(self, obj):
        return obj.qty if obj.qty is not None else obj.duration

    def get_unit_price(self, obj):
        return str(obj.listing_sku.effective_price()) if obj.listing_sku_id else None

    def get_line_subtotal(self, obj):
        units = self._units(obj)
        if not obj.listing_sku_id or units is None:
            return None
        return str(obj.listing_sku.effective_price() * units)

    def get_available(self, obj):
        """False once something has changed since this was added: the SKU
        went inactive, the listing is no longer approved, or stock can no
        longer cover the quantity. The line is kept either way — only
        checkout (a later step) needs to decide what to do about it."""
        sku, listing = obj.listing_sku, obj.listing
        if not sku or not sku.is_active or listing.status != Listing.Status.APPROVED or listing.deleted_at:
            return False
        if obj.qty is not None and sku.stock_qty is not None:
            return sku.stock_qty - sku.reserved_qty >= obj.qty
        return True


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "cart_type", "is_active", "items", "subtotal", "created_at", "updated_at"]

    def get_subtotal(self, obj):
        total = Decimal("0.00")
        for item in obj.items.all():
            units = item.qty if item.qty is not None else item.duration
            if item.listing_sku_id and units is not None:
                total += item.listing_sku.effective_price() * units
        return str(total)


class AddCartItemSerializer(serializers.Serializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=visible_listings())
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
