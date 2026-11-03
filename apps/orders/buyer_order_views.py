"""
The buyer's own orders (`/api/v1/buyer/orders/...`). See
docs/buyer/buyer-api-guide.md.
"""

from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.authentication.permissions import IsBuyerActor
from apps.core.pagination import BuyerPagePagination

from .buyer_order_serializers import (
    BuyerOrderDetailSerializer, BuyerOrderListSerializer, BuyerOrderStatusSerializer, CheckoutSerializer,
)
from .models import Order


class BuyerOrderViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """`GET /buyer/orders/` (page-paginated) — my product orders, newest
    first. `GET /buyer/orders/{id}/` — detail, with the seller, every item,
    the payment and both status histories. `POST /buyer/orders/` —
    checkout. `PATCH /buyer/orders/{id}/` — for now, only `{"status":
    "cancelled"}`, any time before the seller has shipped it."""

    permission_classes = [IsBuyerActor]
    pagination_class = BuyerPagePagination

    def get_queryset(self):
        qs = Order.objects.filter(buyer=self.request.user, order_type=Order.OrderType.PRODUCT)
        if self.action == "retrieve":
            return qs.select_related(
                "seller", "address", "address__country", "address__state", "address__city", "address__thana",
                "payment",
            ).prefetch_related(
                "items", "status_histories", "payment__status_histories",
            )
        return qs.select_related("seller")

    def get_serializer_class(self):
        if self.action == "create":
            return CheckoutSerializer
        if self.action in ("update", "partial_update"):
            return BuyerOrderStatusSerializer
        if self.action == "retrieve":
            return BuyerOrderDetailSerializer
        return BuyerOrderListSerializer

    def create(self, request, *args, **kwargs):
        serializer = CheckoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(BuyerOrderDetailSerializer(order).data, status=201)

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = BuyerOrderStatusSerializer(
            order, data=request.data, partial=kwargs.get("partial", False), context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(BuyerOrderDetailSerializer(order).data)
