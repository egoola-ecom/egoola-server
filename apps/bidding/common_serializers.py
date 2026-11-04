"""
Serializer shared by the seller's own bid write and the admin "do it on a
seller's behalf" write (see services.create_bid/update_bid for the other
half of that sharing).
"""

from rest_framework import serializers

from .models import BidPriceTier


class BidPriceTierSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = BidPriceTier
        fields = ["id", "price_type", "price", "duration", "description", "total_price"]
        extra_kwargs = {
            "total_price": {"read_only": True},
            "price_type": {"required": False, "allow_null": True},
            "price": {"required": False, "min_value": 0},
            "description": {"required": False, "allow_null": True},
        }
