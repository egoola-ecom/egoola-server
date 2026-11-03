"""
Serializers for the buyer's own orders (`/api/v1/buyer/orders/...`). Also
the shared Payment/history serializers reused by the seller's and admin's
own order serializers. See buyer_order_views.py and docs/buyer/buyer-api-guide.md.
"""

from rest_framework import serializers

from apps.accounts.models import Seller
from apps.core.location import LocationNamesMixin

from .models import Address, Cart, Order, OrderItem, OrderStatusChangeHistory, Payment, PaymentGateway, PaymentStatusChangeHistory
from .services import BUYER_CANCELLABLE_FROM, buyer_cancel, create_order_from_cart


class OrderSellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ["id", "name", "phone", "profile_pic_url"]


class OrderAddressSerializer(LocationNamesMixin, serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "name", "phone",
            "country", "country_name", "state", "state_name", "city", "city_name", "thana", "thana_name",
            "address_line1", "address_line2", "zip",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "listing", "listing_sku", "title_snapshot", "price_snapshot", "price_type_snapshot",
            "qty", "duration", "total", "subtotal",
        ]


class PaymentStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentStatusChangeHistory
        fields = [
            "id", "previous_status", "current_status",
            "created_by", "creator_type", "creator_name", "created_at",
        ]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusChangeHistory
        fields = [
            "id", "previous_status", "current_status", "reason",
            "created_by", "creator_type", "creator_name", "created_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """The order's own payment — `store_amount` is only ever filled in by a
    real gateway (bKash, say); cash on delivery leaves it null."""

    status_histories = PaymentStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "status", "amount", "store_amount", "method", "payment_gateway", "gateway_slug",
            "gateway_txn_id", "notes", "meta_data", "status_histories", "created_at", "updated_at",
        ]


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
