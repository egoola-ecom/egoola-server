"""
Admin, read-only oversight of buyers' wishlists: `GET /api/v1/engagement/favourites/`
and `/engagement/favourites/{id}/`. See docs/cart-wishlist-admin-guide.md.

Buyers save, re-save and remove their own favourites through
`apps.engagement.buyer_views` — nothing here can write to one. Unlike that
buyer-facing list, every favourite is shown here regardless of whether its
listing is currently publicly visible (`listing_visible` says which, and can
be filtered on) — an admin needs the full picture.
"""

from django.db.models import Exists, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.authentication.permissions import IsAdminActor
from apps.catalog.public_listings import buyer_visible_listings
from apps.core.pagination import DefaultCursorPagination

from .filters import FavouriteFilter
from .models import Favourite
from .serializers import AdminFavouriteDetailSerializer, AdminFavouriteListSerializer


class AdminFavouriteViewSet(ReadOnlyModelViewSet):
    """List (cursor-paginated) and retrieve only — see FavouriteFilter for
    the filters, `search` for a buyer's name/email/phone or the listing's
    title."""

    permission_classes = [IsAdminActor]
    pagination_class = DefaultCursorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FavouriteFilter
    search_fields = ["buyer__name", "buyer__email", "buyer__phone", "listing__title", "listing__title_bn"]
    ordering_fields = ["created_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        return AdminFavouriteListSerializer if self.action == "list" else AdminFavouriteDetailSerializer

    def get_queryset(self):
        visible = Exists(buyer_visible_listings().filter(pk=OuterRef("listing_id")))
        return Favourite.objects.select_related("buyer", "listing", "listing__seller").annotate(
            listing_visible=visible
        )
