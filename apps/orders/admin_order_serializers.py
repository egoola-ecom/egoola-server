"""
Serializers for the admin order panel (`/api/v1/orders/orders/...`). See
admin_order_views.py and docs/admin/admin-management-guide.md.
"""

from rest_framework import serializers

from apps.accounts.admin_api.serializers import BuyerListSerializer

from .buyer_order_serializers import (
    OrderAddressSerializer, OrderItemSerializer, OrderSellerSerializer, OrderStatusHistorySerializer, PaymentSerializer,
)
from .models import Order


class AdminOrderListSerializer(serializers.ModelSerializer):
    buyer = BuyerListSerializer(read_only=True)
    seller = OrderSellerSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_type", "buyer", "seller", "status", "payment_status", "subtotal", "delivery_cost",
            "discount", "total", "payable", "created_at", "updated_at",
        ]


class AdminOrderDetailSerializer(AdminOrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = OrderAddressSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)
    status_histories = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta(AdminOrderListSerializer.Meta):
        fields = AdminOrderListSerializer.Meta.fields + [
            "items", "address", "payment", "status_histories",
            "expected_delivery_at", "completed_at", "cancelled_reason", "rejected_reason",
            "created_by", "creator_type", "creator_name", "updated_by", "updater_type", "updater_name",
        ]


class AdminOrderStatusSerializer(serializers.Serializer):
    """`{"status": "...", "reason": "..."}` — admin can move an order to
    any status at any time, no transition check."""

    status = serializers.ChoiceField(choices=Order.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True)

    def update(self, instance, validated_data):
        from .services import admin_set_status
        return admin_set_status(instance, validated_data["status"], self.context["request"].user, validated_data.get("reason"))
