"""
Serializer for the buyer's own saved delivery addresses
(`/api/v1/buyer/addresses/...`). See buyer_address_views.py.
"""

from rest_framework import serializers

from apps.core.location import LocationConsistencyMixin, LocationNamesMixin

from .models import Address


class BuyerAddressSerializer(LocationConsistencyMixin, LocationNamesMixin, serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "name", "phone",
            "country", "country_name", "state", "state_name", "city", "city_name", "thana", "thana_name",
            "address_line1", "address_line2", "zip", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
