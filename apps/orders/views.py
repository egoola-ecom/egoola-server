"""
Admin, read-only oversight of buyers' carts: `GET /api/v1/orders/carts/` and
`/orders/carts/{id}/`. See docs/cart-wishlist-admin-guide.md.

Buyers create, change and clear their own carts through
`apps.orders.buyer_views` — nothing here can write to one. Every cart is
shown regardless of whether its listings are still publicly visible; an
admin needs the full picture, not the buyer-facing visibility rule.
"""

from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.authentication.permissions import IsAdminActor
from apps.core.pagination import DefaultCursorPagination

from .filters import CartFilter
from .models import Cart, CartItem
from .serializers import AdminCartDetailSerializer, AdminCartListSerializer


class AdminCartViewSet(ReadOnlyModelViewSet):
    """List (cursor-paginated) and retrieve only — see CartFilter for the
    filters, `search` for a buyer's name/email/phone."""

    permission_classes = [IsAdminActor]
    pagination_class = DefaultCursorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CartFilter
    search_fields = ["buyer__name", "buyer__email", "buyer__phone"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        return AdminCartListSerializer if self.action == "list" else AdminCartDetailSerializer

    def get_queryset(self):
        queryset = Cart.objects.select_related("buyer").annotate(item_count=Count("items"))
        if self.action == "list":
            return queryset
        items = Prefetch(
            "items",
            queryset=CartItem.objects.select_related("listing", "listing_sku").order_by("id"),
        )
        return queryset.prefetch_related(items)
