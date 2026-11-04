"""
Every serializer for the buyer's own cart, saved addresses, and orders
(`/api/v1/buyer/cart|addresses|orders/...`). See buyer/views.py and
docs/buyer/buyer-api-guide.md.
"""

from rest_framework import serializers

from apps.catalog.models import Listing, ListingSku
from apps.catalog.public.listings import buyer_visible_listings
from apps.core.location import LocationConsistencyMixin, LocationNamesMixin

from ..common_serializers import OrderAddressSerializer, OrderItemSerializer, OrderSellerSerializer, OrderStatusHistorySerializer, PaymentSerializer
from ..models import Address, Cart, CartItem, Order, PaymentGateway
from ..services import BUYER_CANCELLABLE_FROM, buyer_cancel, create_order_from_cart


# --- Cart -------------------------------------------------------------------

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


class CartSellerSerializer(serializers.Serializer):
    """None when this cart holds admin-owned listings (no seller)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    profile_pic_url = serializers.CharField()


class CartSerializer(serializers.ModelSerializer):
    seller = serializers.SerializerMethodField()
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "cart_type", "seller", "is_active", "items", "subtotal", "created_at", "updated_at"]

    def get_seller(self, obj):
        if not obj.seller_id:
            return None
        return CartSellerSerializer(obj.seller).data

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class CartSummarySerializer(serializers.ModelSerializer):
    """One row per active cart, for a header badge / "all carts" dropdown —
    no items, just the counts a list screen needs. `item_count` is the
    number of lines (not units: duration isn't a count, so a product cart's
    qty total and a service cart's duration total can't be added together
    meaningfully — line count is the one thing that's comparable across
    both kinds)."""

    seller = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "cart_type", "seller", "item_count", "subtotal", "updated_at"]

    def get_seller(self, obj):
        if not obj.seller_id:
            return None
        return CartSellerSerializer(obj.seller).data

    def get_item_count(self, obj):
        return len(obj.items.all())

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


# --- Addresses ---------------------------------------------------------------

class BuyerAddressSerializer(LocationConsistencyMixin, LocationNamesMixin, serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "name", "phone",
            "country", "country_name", "state", "state_name", "city", "city_name", "thana", "thana_name",
            "address_line1", "address_line2", "zip", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# --- Orders -------------------------------------------------------------------

class BuyerOrderListSerializer(serializers.ModelSerializer):
    seller = OrderSellerSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_type", "seller", "status", "payment_status", "subtotal", "delivery_cost", "discount",
            "total", "payable", "created_at", "updated_at",
        ]


class BuyerOrderDetailSerializer(BuyerOrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = OrderAddressSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)
    status_histories = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta(BuyerOrderListSerializer.Meta):
        fields = BuyerOrderListSerializer.Meta.fields + [
            "items", "address", "payment", "status_histories",
            "expected_delivery_at", "completed_at", "cancelled_reason", "rejected_reason",
        ]


class CheckoutSerializer(serializers.Serializer):
    """`{"cart": <id>, "address": <id>, "payment_gateway": <id>}` — order,
    order items and the payment are all created in this one call."""

    cart = serializers.PrimaryKeyRelatedField(queryset=Cart.objects.filter(is_active=True))
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    payment_gateway = serializers.PrimaryKeyRelatedField(queryset=PaymentGateway.objects.filter(is_active=True))

    def validate(self, attrs):
        actor = self.context["request"].user
        cart, address = attrs["cart"], attrs["address"]
        if cart.buyer_id != actor.id:
            raise serializers.ValidationError({"cart": "Not your cart."})
        if address.addressable_type != Address.AddressableType.USER or address.addressable_id != actor.id:
            raise serializers.ValidationError({"address": "Not your saved address."})
        return attrs

    def create(self, validated_data):
        actor = self.context["request"].user
        try:
            return create_order_from_cart(
                validated_data["cart"], validated_data["address"], validated_data["payment_gateway"], actor,
            )
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class BuyerOrderStatusSerializer(serializers.Serializer):
    """`{"status": "cancelled", "reason": "..."}` — the only move a buyer
    can make for now; more may come later."""

    status = serializers.ChoiceField(choices=Order.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_status(self, status):
        if status != Order.Status.CANCELLED:
            raise serializers.ValidationError("A buyer can currently only move an order to cancelled.")
        return status

    def validate(self, attrs):
        if self.instance.status not in BUYER_CANCELLABLE_FROM:
            raise serializers.ValidationError({"status": "This order can no longer be cancelled."})
        return attrs

    def update(self, instance, validated_data):
        return buyer_cancel(instance, self.context["request"].user, validated_data.get("reason"))
