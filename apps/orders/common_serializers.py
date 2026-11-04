"""
Serializers shared by every role's own order serializers — the address,
item, payment and history shapes a buyer, a seller and an admin all see
inside an order detail, so the three surfaces can never drift on shape.
"""

from rest_framework import serializers

from apps.accounts.models import Seller
from apps.core.location import LocationNamesMixin

from .models import Address, OrderItem, OrderStatusChangeHistory, Payment, PaymentStatusChangeHistory


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
