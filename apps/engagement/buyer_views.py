"""
The buyer's own wishlist (`/api/v1/buyer/favourites/...`). See
docs/buyer-api-guide.md.

Unlike the cart, favouriting is a plain, idempotent toggle: saving an
already-saved listing changes nothing, and un-saving one that was never
saved (or already removed) is not an error either.
"""

from django.db.models import Prefetch
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.public_views import public_seller_listings_q
from apps.authentication.permissions import IsBuyerActor
from apps.catalog.models import Listing, ListingSku
from apps.core.pagination import BuyerPagePagination

from .buyer_serializers import AddFavouriteSerializer, FavouriteSerializer
from .models import Favourite

_ACTIVE_SKUS = Prefetch("listing__skus", queryset=ListingSku.objects.filter(is_active=True))


class FavouriteListCreateView(ListCreateAPIView):
    """GET `?type=product|service` (optional) — the buyer's saved listings,
    newest first. A favourite whose listing has since gone private (seller
    paused, listing rejected, ...) drops out of this list but is kept as-is —
    it reappears on its own once the listing is public again, same as
    browsing (see public-api-guide.md).

    POST `{listing}` — save a listing. Favouriting an already-saved one just
    returns the existing row (`200`, not a duplicate or an error)."""

    permission_classes = [IsBuyerActor]
    pagination_class = BuyerPagePagination

    def get_serializer_class(self):
        return AddFavouriteSerializer if self.request.method == "POST" else FavouriteSerializer

    def get_queryset(self):
        catalog_type = self.request.query_params.get("type")
        if catalog_type is not None and catalog_type not in Listing.CatalogType.values:
            raise ValidationError({"type": [f"Must be one of {', '.join(Listing.CatalogType.values)}."]})

        queryset = Favourite.objects.filter(
            buyer=self.request.user,
            listing__status=Listing.Status.APPROVED,
        ).filter(public_seller_listings_q(prefix="listing__seller"))
        if catalog_type:
            queryset = queryset.filter(listing__catalog_type=catalog_type)
        return queryset.select_related(
            "listing__category", "listing__brand", "listing__seller"
        ).prefetch_related(_ACTIVE_SKUS).order_by("-created_at", "-id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.validated_data["listing"]
        actor = request.user

        favourite, created = Favourite.objects.get_or_create(
            buyer=actor, listing=listing,
            defaults={"created_by": actor.id, "creator_type": actor.actor_type, "creator_name": actor.name},
        )
        return Response(
            FavouriteSerializer(favourite, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FavouriteDeleteView(APIView):
    """DELETE `/buyer/favourites/{listing_id}/` — un-save, keyed by the
    listing's own id (not the favourite row's), since the frontend already
    has it from the listing it's showing a heart icon on. Always `204`,
    whether or not it was actually saved."""

    permission_classes = [IsBuyerActor]

    def delete(self, request, listing_id):
        Favourite.objects.filter(buyer=request.user, listing_id=listing_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
