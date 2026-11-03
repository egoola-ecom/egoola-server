"""
The seller's own orders (`/api/v1/seller/orders/...`). See
docs/seller/seller-api-guide.md.
"""

from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.authentication.permissions import IsActiveVerifiedSellerActor
from apps.core.pagination import DefaultCursorPagination

from .filters import SellerOrderFilter
from .models import Order
from .seller_order_serializers import SellerOrderDetailSerializer, SellerOrderListSerializer, SellerOrderStatusSerializer


class SellerOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """`GET /seller/orders/` (cursor-paginated) — orders placed with me.
    `GET /seller/orders/{id}/` — detail, with the buyer, every item, the
    payment and both status histories. `PATCH /seller/orders/{id}/` — move
    it forward: accept, reject (reason required), in_progress, shipped,
    delivered. The response is always the full detail shape, same as a GET."""

    permission_classes = [IsActiveVerifiedSellerActor]
    pagination_class = DefaultCursorPagination
    filterset_class = SellerOrderFilter
    search_fields = ["buyer__name", "buyer__phone", "buyer__email"]

    def get_queryset(self):
        qs = Order.objects.filter(seller=self.request.user, order_type=Order.OrderType.PRODUCT)
        if self.action == "retrieve":
            return qs.select_related(
                "buyer", "address", "address__country", "address__state", "address__city", "address__thana",
                "payment",
            ).prefetch_related(
                "items", "status_histories", "payment__status_histories",
            )
        return qs.select_related("buyer")

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return SellerOrderStatusSerializer
        if self.action == "retrieve":
            return SellerOrderDetailSerializer
        return SellerOrderListSerializer

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = SellerOrderStatusSerializer(
            order, data=request.data, partial=kwargs.get("partial", False), context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(SellerOrderDetailSerializer(order).data)
