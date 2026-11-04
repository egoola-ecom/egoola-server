from rest_framework import serializers

from ..models import PaymentGateway


class PublicPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = ["id", "name", "slug", "icon_url"]
