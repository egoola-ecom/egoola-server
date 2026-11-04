"""
Serializers for the seller's own orders (`/api/v1/seller/orders/...`). See
seller/views.py and docs/seller/seller-order-api-guide.md.
"""

from rest_framework import serializers

from apps.accounts.admin_api.serializers import BuyerListSerializer

from ..common_serializers import OrderAddressSerializer, OrderItemSerializer, OrderStatusHistorySerializer, PaymentSerializer
from ..models import Order
from ..services import SELLER_TRANSITIONS


class SellerOrderListSerializer(serializers.ModelSerializer):
    buyer = BuyerListSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_type", "buyer", "status", "payment_status", "subtotal", "delivery_cost", "discount",
            "total", "payable", "created_at", "updated_at",
        ]


class SellerOrderDetailSerializer(SellerOrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = OrderAddressSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)
    status_histories = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta(SellerOrderListSerializer.Meta):
        fields = SellerOrderListSerializer.Meta.fields + [
            "items", "address", "payment", "status_histories",
            "expected_delivery_at", "completed_at", "cancelled_reason", "rejected_reason",
        ]


class SellerOrderStatusSerializer(serializers.Serializer):
    """`{"status": "accepted"|"rejected"|"in_progress"|"shipped"|"delivered",
    "reason": "..."}` — one step forward at a time (SELLER_TRANSITIONS);
    `reason` is required to reject, buyer-visible."""

    status = serializers.ChoiceField(choices=Order.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        allowed = SELLER_TRANSITIONS.get(self.instance.status, set())
        if attrs["status"] not in allowed:
            raise serializers.ValidationError(
                {"status": f"Cannot move an order from {self.instance.status} to {attrs['status']}."}
            )
        if attrs["status"] == Order.Status.REJECTED and not attrs.get("reason"):
            raise serializers.ValidationError({"reason": "A reason is required to reject an order."})
        return attrs

    def update(self, instance, validated_data):
        from ..services import seller_set_status
        return seller_set_status(instance, validated_data["status"], self.context["request"].user, validated_data.get("reason"))
