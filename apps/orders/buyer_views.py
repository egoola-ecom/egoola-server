"""
The buyer's own cart (`/api/v1/buyer/cart/...`). See docs/buyer-api-guide.md.

A buyer has at most one *active* cart per type (product / service — see
Cart.CatalogType); which one a GET/DELETE acts on is picked with `?type=`.
Adding an item instead picks the cart automatically, from the listing's own
type — the buyer never states it directly, so it can never mismatch.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsBuyerActor

from .buyer_serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
    variant_snapshot,
)
from .models import Cart, CartItem

ITEM_PREFETCH = (
    "items__listing",
    "items__listing_sku__variants__attribute",
    "items__listing_sku__variants__attribute_value",
)


def _cart_type(request):
    value = request.query_params.get("type")
    if value not in Cart.CatalogType.values:
        raise ValidationError({"type": [f"Must be one of {', '.join(Cart.CatalogType.values)}."]})
    return value


def _get_or_create_active_cart(buyer, cart_type):
    return Cart.objects.get_or_create(
        buyer=buyer, cart_type=cart_type, is_active=True,
        defaults={"created_by": buyer.id, "creator_type": buyer.actor_type, "creator_name": buyer.name},
    )[0]


class CartView(APIView):
    """GET `?type=product|service` — the buyer's active cart of that type
    (created empty on first touch). DELETE empties it; the cart row itself
    stays active for further adds (it only closes at checkout)."""

    permission_classes = [IsBuyerActor]

    def get(self, request):
        cart = _get_or_create_active_cart(request.user, _cart_type(request))
        cart = Cart.objects.prefetch_related(*ITEM_PREFETCH).get(pk=cart.pk)
        return Response(CartSerializer(cart).data)

    def delete(self, request):
        cart = _get_or_create_active_cart(request.user, _cart_type(request))
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemsView(APIView):
    """POST — add a listing + SKU to the matching cart, merging into an
    existing line for the same SKU (qty/duration add up) instead of
    duplicating it."""

    permission_classes = [IsBuyerActor]

    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.validated_data["listing"]
        sku = serializer.validated_data["listing_sku"]
        qty = serializer.validated_data.get("qty")
        duration = serializer.validated_data.get("duration")
        actor = request.user

        with transaction.atomic():
            cart = _get_or_create_active_cart(actor, listing.catalog_type)
            item = CartItem.objects.select_for_update().filter(cart=cart, listing_sku=sku).first()
            if item:
                if qty is not None:
                    item.qty = (item.qty or 0) + qty
                if duration is not None:
                    item.duration = (item.duration or 0) + duration
                item.updated_by, item.updater_type, item.updater_name = actor.id, actor.actor_type, actor.name
                item.save()
            else:
                item = CartItem.objects.create(
                    cart=cart, listing=listing, listing_sku=sku, qty=qty, duration=duration,
                    created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
                    **variant_snapshot(sku),
                )
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    """PATCH / DELETE one line of the logged-in buyer's own cart."""

    permission_classes = [IsBuyerActor]

    def get_object(self, request, pk):
        return get_object_or_404(CartItem, pk=pk, cart__buyer=request.user, cart__is_active=True)

    def patch(self, request, pk):
        item = self.get_object(request, pk)
        actor = request.user
        serializer = UpdateCartItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name)
        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = self.get_object(request, pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
