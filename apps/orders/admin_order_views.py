"""
Admin, full oversight of product orders (`/api/v1/orders/orders/...`). List
and detail only — for now admin can just move the status, any status to any
status, no transition check (unlike the seller's own endpoint).
"""

from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminActor
from apps.core.pagination import DefaultCursorPagination

from .admin_order_serializers import AdminOrderDetailSerializer, AdminOrderListSerializer, AdminOrderStatusSerializer
from .filters import AdminOrderFilter
from .models import Order


class AdminOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """`PATCH` always answers with the full detail shape (buyer, seller,
    items, address, payment, both status histories), same as a `GET`."""

    permission_classes = [IsAdminActor]
    pagination_class = DefaultCursorPagination
    filterset_class = AdminOrderFilter
    search_fields = ["buyer__name", "buyer__phone", "seller__name"]

    def get_queryset(self):
        qs = Order.objects.filter(order_type=Order.OrderType.PRODUCT)
        if self.action == "retrieve":
            return qs.select_related(
                "buyer", "seller", "address",
                "address__country", "address__state", "address__city", "address__thana",
                "payment",
            ).prefetch_related(
                "items", "status_histories", "payment__status_histories",
            )
        return qs.select_related("buyer", "seller")

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return AdminOrderStatusSerializer
        if self.action == "retrieve":
            return AdminOrderDetailSerializer
        return AdminOrderListSerializer

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = AdminOrderStatusSerializer(
            order, data=request.data, partial=kwargs.get("partial", False), context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(AdminOrderDetailSerializer(order).data)
