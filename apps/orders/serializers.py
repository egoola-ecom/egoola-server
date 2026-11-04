"""
Admin, read-only oversight of buyers' carts (`/api/v1/orders/carts/...`).
Buyers manage their own cart through `apps.orders.buyer_views` instead —
nothing here ever writes to a cart. See docs/admin/cart-wishlist-admin-guide.md.
"""

from rest_framework import serializers

from apps.accounts.admin_api.serializers import BuyerListSerializer
from config.storage import delete_upload, save_upload

from .buyer_serializers import CartItemListingSerializer, CartItemSkuSerializer
from .models import Cart, CartItem, PaymentGateway, _generate_gateway_slug


class AdminCartItemSerializer(serializers.ModelSerializer):
    listing = CartItemListingSerializer(read_only=True)
    listing_sku = CartItemSkuSerializer(read_only=True)
    unit_price = serializers.SerializerMethodField()
    line_subtotal = serializers.SerializerMethodField()
    available = serializers.BooleanField(source="is_available", read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id", "listing", "listing_sku", "qty", "duration", "color", "size",
            "unit_price", "line_subtotal", "available",
            "created_by", "creator_type", "creator_name",
            "updated_by", "updater_type", "updater_name",
            "created_at", "updated_at",
        ]

    def get_unit_price(self, obj):
        return str(obj.unit_price) if obj.unit_price is not None else None

    def get_line_subtotal(self, obj):
        return str(obj.line_subtotal) if obj.line_subtotal is not None else None


class AdminCartSellerSerializer(serializers.Serializer):
    """None when this cart holds admin-owned listings (no seller)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    verification_status = serializers.CharField()


class AdminCartListSerializer(serializers.ModelSerializer):
    """One row per cart: who it belongs to, which seller (a cart never spans
    sellers — see the Cart model docstring), whether it is still open, and a
    quick total — the line items themselves are only on the detail view."""

    buyer = BuyerListSerializer(read_only=True)
    seller = serializers.SerializerMethodField()
    item_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id", "buyer", "seller", "cart_type", "is_active", "order", "item_count", "subtotal",
            "created_at", "updated_at",
        ]

    def get_seller(self, obj):
        return AdminCartSellerSerializer(obj.seller).data if obj.seller_id else None

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class AdminCartDetailSerializer(AdminCartListSerializer):
    items = AdminCartItemSerializer(many=True, read_only=True)

    class Meta(AdminCartListSerializer.Meta):
        fields = AdminCartListSerializer.Meta.fields + [
            "items", "created_by", "creator_type", "creator_name",
            "updated_by", "updater_type", "updater_name",
        ]


class PaymentGatewaySerializer(serializers.ModelSerializer):
    """`slug` is always server-generated from `name` (on create, and again on
    a rename) — never taken from the client. `icon` is optional; sending one
    replaces the old file, `icon_path`/`icon_url` are always server-computed."""

    icon = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PaymentGateway
        fields = ["id", "name", "slug", "icon", "icon_path", "icon_url", "is_active", "created_at", "updated_at"]
        read_only_fields = ["slug", "icon_path", "icon_url", "created_at", "updated_at"]

    def _apply_icon(self, instance, icon):
        old_path = instance.icon_path
        instance.icon_path, instance.icon_url = save_upload(icon, "payment-gateways")
        instance.save(update_fields=["icon_path", "icon_url"])
        if old_path and old_path != instance.icon_path:
            delete_upload(old_path)

    def create(self, validated_data):
        icon = validated_data.pop("icon", None)
        validated_data["slug"] = _generate_gateway_slug(validated_data["name"])
        instance = super().create(validated_data)
        if icon is not None:
            self._apply_icon(instance, icon)
        return instance

    def update(self, instance, validated_data):
        icon = validated_data.pop("icon", None)
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = _generate_gateway_slug(validated_data["name"])
        instance = super().update(instance, validated_data)
        if icon is not None:
            self._apply_icon(instance, icon)
        return instance
