"""
Every admin view for carts, Payment Gateways, and orders
(`/api/v1/orders/carts|payment-gateways|orders/...`).

Buyers create, change and clear their own carts through
`apps.orders.buyer.views` — nothing here can write to one. Every cart is
shown regardless of whether its listings are still publicly visible; an
admin needs the full picture, not the buyer-facing visibility rule.

Admin order oversight is list and detail, plus an unrestricted status
override (any status to any status, no transition check) — unlike the
seller's own endpoint. See docs/admin/cart-wishlist-admin-guide.md,
docs/admin/admin-payment-gateway-api-guide.md, docs/admin/admin-order-api-guide.md.
"""

from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.authentication.permissions import IsAdminActor
from apps.core.mixins import AuditedViewSetMixin
from apps.core.pagination import DefaultCursorPagination
from config.storage import delete_upload

from ..models import Cart, CartItem, Order, PaymentGateway
from .filters import AdminOrderFilter, CartFilter
from .serializers import (
    AdminCartDetailSerializer, AdminCartListSerializer, AdminOrderDetailSerializer, AdminOrderListSerializer,
    AdminOrderStatusSerializer, PaymentGatewaySerializer,
)


class AdminCartViewSet(ReadOnlyModelViewSet):
    """List (cursor-paginated) and retrieve only — see CartFilter for the
    filters, `search` for a buyer's name/email/phone."""

    permission_classes = [IsAdminActor]
    pagination_class = DefaultCursorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CartFilter
    search_fields = ["buyer__name", "buyer__email", "buyer__phone", "seller__name", "seller__email"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        return AdminCartListSerializer if self.action == "list" else AdminCartDetailSerializer

    def get_queryset(self):
        queryset = Cart.objects.select_related("buyer", "seller").annotate(item_count=Count("items"))
        if self.action == "list":
            return queryset
        items = Prefetch(
            "items",
            queryset=CartItem.objects.select_related("listing", "listing_sku").order_by("id"),
        )
        return queryset.prefetch_related(items)


class AdminPaymentGatewayViewSet(
    AuditedViewSetMixin, mixins.ListModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    """Payment Gateway Management — list / create / update / delete. No
    retrieve: the list row already carries everything there is. Create and
    update take multipart form data when sending an icon file."""

    permission_classes = [IsAdminActor]
    queryset = PaymentGateway.objects.all()
    serializer_class = PaymentGatewaySerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]

    def perform_destroy(self, instance):
        path = instance.icon_path
        instance.delete()
        delete_upload(path)


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
