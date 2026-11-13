"""
Every view for the buyer's own cart, saved addresses, and orders
(`/api/v1/buyer/cart|addresses|orders/...`). See docs/buyer/buyer-api-guide.md.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsBuyerActor
from apps.core.pagination import BuyerPagePagination

from ..models import Address, Cart, CartItem, Order
from .filters import BuyerOrderFilter
from .serializers import (
    AddCartItemSerializer,
    BuyerAddressSerializer,
    BuyerOrderDetailSerializer,
    BuyerOrderListSerializer,
    BuyerOrderStatusSerializer,
    CartItemSerializer,
    CartSerializer,
    CartSummarySerializer,
    CheckoutSerializer,
    UpdateCartItemSerializer,
    variant_snapshot,
)

# --- Cart ---------------------------------------------------------------------

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


def _get_or_create_active_cart(buyer, cart_type, seller):
    return Cart.objects.get_or_create(
        buyer=buyer, cart_type=cart_type, seller=seller, is_active=True,
        defaults={"created_by": buyer.id, "creator_type": buyer.actor_type, "creator_name": buyer.name},
    )[0]


def _touch(cart, actor):
    """Bumps `updated_at` on the cart itself and stamps who did it — changing
    one of its items doesn't otherwise touch the cart row, and "most recently
    touched" (see `_target_cart`) needs to mean any interaction with it, not
    just its own field changes."""
    cart.updated_by, cart.updater_type, cart.updater_name = actor.id, actor.actor_type, actor.name
    cart.save(update_fields=["updated_at", "updated_by", "updater_type", "updater_name"])


def _target_cart(request):
    """The one cart GET/DELETE act on: `?seller=` names it exactly (`0` = the
    shared cart for admin-owned listings, no seller); left out, it's whichever
    active cart of that type the buyer touched most recently. `None` if no
    such cart exists — this never creates one."""
    queryset = Cart.objects.filter(buyer=request.user, cart_type=_cart_type(request), is_active=True)
    seller = request.query_params.get("seller")
    if seller is not None:
        if not seller.isdigit():
            raise ValidationError({"seller": ["Must be a whole number."]})
        seller_id = int(seller)
        queryset = queryset.filter(seller_id=seller_id or None)
    return queryset.order_by("-updated_at", "-id").first()


class CartView(APIView):
    """GET `?type=product|service[&seller=]` — one cart (or `null`): the named
    seller's, or the most recently touched one of that type if `seller` is
    left out. DELETE empties that same cart (no-op if there is none); the
    row itself stays active either way (it only closes at checkout)."""

    permission_classes = [IsBuyerActor]

    def get(self, request):
        cart = _target_cart(request)
        if cart is None:
            return Response(None)
        cart = Cart.objects.select_related("seller").prefetch_related(*ITEM_PREFETCH).get(pk=cart.pk)
        return Response(CartSerializer(cart).data)

    def delete(self, request):
        cart = _target_cart(request)
        if cart is not None:
            cart.items.all().delete()
            _touch(cart, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartSummaryView(APIView):
    """GET — one row per active cart (`cart_type`, `seller`, `item_count`,
    `subtotal`, `updated_at`), plus a grand `item_count` across every cart.
    For a header badge and an "all carts" view — this never creates a cart,
    it only ever lists what already exists."""

    permission_classes = [IsBuyerActor]

    def get(self, request):
        carts = Cart.objects.filter(buyer=request.user, is_active=True).select_related(
            "seller"
        ).prefetch_related("items__listing_sku").order_by("-updated_at", "-id")
        rows = CartSummarySerializer(carts, many=True).data
        return Response({"item_count": sum(row["item_count"] for row in rows), "carts": rows})


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
            cart = _get_or_create_active_cart(actor, listing.catalog_type, listing.seller)
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
            _touch(cart, actor)
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
        _touch(item.cart, actor)
        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = self.get_object(request, pk)
        cart = item.cart
        actor = request.user
        item.delete()
        _touch(cart, actor)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Addresses -----------------------------------------------------------------

class BuyerAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsBuyerActor]
    serializer_class = BuyerAddressSerializer
    pagination_class = None  # a buyer never has enough saved addresses to paginate

    def get_queryset(self):
        return Address.objects.filter(
            addressable_type=Address.AddressableType.USER, addressable_id=self.request.user.id,
        ).select_related("country", "state", "city", "thana").order_by("-created_at")

    def perform_create(self, serializer):
        actor = self.request.user
        serializer.save(
            addressable_type=Address.AddressableType.USER, addressable_id=actor.id,
            created_by=actor.id, creator_type=actor.actor_type, creator_name=actor.name,
        )

    def perform_update(self, serializer):
        actor = self.request.user
        serializer.save(updated_by=actor.id, updater_type=actor.actor_type, updater_name=actor.name)


# --- Orders ---------------------------------------------------------------------

class BuyerOrderViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """`GET /buyer/orders/` (page-paginated) — my product and gig orders,
    newest first. `GET /buyer/orders/{id}/` — detail, with the seller, every
    item, the payment and both status histories. `POST /buyer/orders/` —
    checkout. `PATCH /buyer/orders/{id}/` — for now, only `{"status":
    "cancelled"}`, any time before the seller has shipped it.

    A job's own order (created when a bid is accepted, no cart involved) is
    reached through `/buyer/jobs/{id}/` instead, not this list."""

    permission_classes = [IsBuyerActor]
    pagination_class = BuyerPagePagination
    filterset_class = BuyerOrderFilter

    def get_queryset(self):
        qs = Order.objects.filter(
            buyer=self.request.user, order_type__in=[Order.OrderType.PRODUCT, Order.OrderType.SERVICE],
        )
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
