"""
Public, read-only payment-gateway list — for the checkout form's gateway
picker, which runs for a logged-in buyer/seller but must not depend on an
admin token to find out which gateway ids exist.

Deliberately a separate set of endpoints from the admin payment-gateway API
(`/api/v1/orders/payment-gateways/`), not a loosened version of it: those
rows carry audit columns and accept writes, and also list inactive gateways
(an admin re-enabling one). This returns only active gateways, and only GET.

`authentication_classes = []` so a stale or expired token in the browser can
never turn a public read into a 401.
"""

from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import AllowAny

from .models import PaymentGateway


class PublicPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = ["id", "name", "slug", "icon_url"]


class PublicPaymentGatewayViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicPaymentGatewaySerializer
    queryset = PaymentGateway.objects.filter(is_active=True)
    pagination_class = None
