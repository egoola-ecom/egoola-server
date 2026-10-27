"""
Admin, read-only oversight of buyers' carts (`/api/v1/orders/carts/...`).
Buyers manage their own cart through `apps.orders.buyer_views` instead —
nothing here ever writes to a cart. See docs/cart-wishlist-admin-guide.md.
"""

from rest_framework import serializers

from apps.accounts.serializers import BuyerListSerializer

from .buyer_serializers import CartItemListingSerializer, CartItemSkuSerializer
from .models import Cart, CartItem


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


class AdminCartListSerializer(serializers.ModelSerializer):
    """One row per cart: who it belongs to, what kind, whether it is still
    open, and a quick total — the line items themselves are only on the
    detail view."""

    buyer = BuyerListSerializer(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id", "buyer", "cart_type", "is_active", "order", "item_count", "subtotal",
            "created_at", "updated_at",
        ]

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class AdminCartDetailSerializer(AdminCartListSerializer):
    items = AdminCartItemSerializer(many=True, read_only=True)

    class Meta(AdminCartListSerializer.Meta):
        fields = AdminCartListSerializer.Meta.fields + [
            "items", "created_by", "creator_type", "creator_name",
            "updated_by", "updater_type", "updater_name",
        ]
