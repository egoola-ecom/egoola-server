"""
The seller's own listing endpoints (`/api/v1/seller/listings/` for products,
`/api/v1/seller/gigs/` for gigs), the job board (`/api/v1/seller/jobs/...`),
and the read-only lookups a seller needs to fill the listing form
(`/api/v1/seller/lookups/...`).

Only a seller who can operate (verified AND active) may use them — see
IsActiveVerifiedSellerActor. A seller sees and changes only their own
listings. There is no delete: only an admin can delete a listing.
"""

from django.db import transaction
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import JSONParser

from apps.authentication.permissions import IsActiveVerifiedSellerActor
from apps.bidding.models import Bid
from apps.core.mixins import AuditedViewSetMixin
from apps.core.pagination import DefaultCursorPagination, LargeListPagination

from ..models import Attribute, Brand, Category, Listing, Measurement
from .filters import SellerGigFilter, SellerJobFilter, SellerListingFilter
from .serializers import (
    SellerAttributeLookupSerializer,
    SellerBrandLookupSerializer,
    SellerCategoryLookupSerializer,
    SellerGigListSerializer,
    SellerGigSerializer,
    SellerJobDetailSerializer,
    SellerJobListSerializer,
    SellerListingListSerializer,
    SellerListingSerializer,
    SellerMeasurementLookupSerializer,
)


class _SellerListingBaseViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Create, list, see and edit my listings (products or gigs, see the two
    subclasses). No delete.

    Create: always `pending`, owned by the logged-in seller. Edit (PATCH / PUT):
    a `rejected` or `changes_requested` listing goes back to `pending`; an
    `approved` or `pending` listing keeps its status. Pictures and videos are not
    sent here (JSON only): see apps.catalog.listing_files. See SellerListingMixin."""

    permission_classes = [IsActiveVerifiedSellerActor]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ["created_at", "updated_at", "requested_at", "title", "status", "id"]
    ordering = ["-created_at", "-id"]
    parser_classes = [JSONParser]

    # What the subclass decides: the rows it may touch and its serializers.
    scope = Q()
    serializer_class = None
    list_serializer_class = None

    def get_serializer_class(self):
        return self.list_serializer_class if self.action == "list" else self.serializer_class

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def get_queryset(self):
        # Always limited to the logged-in seller's own, non-deleted listings of this kind.
        queryset = Listing.objects.filter(self.scope, seller=self.request.user)
        if self.action in ("update", "partial_update"):
            # Lock the row for the whole save, so an admin's decision made at the
            # same moment cannot be overwritten by this (older) copy of the listing.
            return queryset.select_for_update(of=("self",))
        if self.action == "list":
            return queryset.select_related("category", "brand").prefetch_related("skus")
        return queryset.select_related(
            "category", "brand", "measurement", "country", "state", "city", "thana"
        ).prefetch_related(
            "price_tiers", "media", "status_change_logs", "skus__variants__attribute", "skus__variants__attribute_value"
        )


class SellerListingViewSet(_SellerListingBaseViewSet):
    """My products (`/seller/listings/`). My gigs are on `/seller/gigs/`; a gig id
    here is a 404."""

    scope = Q(catalog_type=Listing.CatalogType.PRODUCT)
    serializer_class = SellerListingSerializer
    list_serializer_class = SellerListingListSerializer
    filterset_class = SellerListingFilter
    search_fields = ["title", "title_bn", "skus__sku", "brand__name"]


class SellerGigViewSet(_SellerListingBaseViewSet):
    """My gigs (`/seller/gigs/`): service offers, priced by SKUs (one per price
    type). A product id here is a 404."""

    scope = Q(catalog_type=Listing.CatalogType.SERVICE, posted_by_role=Listing.PostedByRole.SELLER_OFFER)
    serializer_class = SellerGigSerializer
    list_serializer_class = SellerGigListSerializer
    filterset_class = SellerGigFilter
    search_fields = ["title", "title_bn", "skus__sku"]


# ------------------------------------------------------------------ job board


class SellerJobViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """`GET /seller/jobs/` — the job board: open jobs only, filtered by
    SellerJobFilter. `GET /seller/jobs/{id}/` — a job I can see (open, or one
    I've bid on), with my own bids on it embedded. `GET /seller/jobs/mine/` —
    jobs I've bid on, any status; add `?won=true` for only the ones where my
    own bid is currently accepted or completed (the jobs I actually got)."""

    permission_classes = [IsActiveVerifiedSellerActor]
    pagination_class = DefaultCursorPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SellerJobFilter
    ordering_fields = ["created_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        return SellerJobDetailSerializer if self.action == "retrieve" else SellerJobListSerializer

    def _scoped(self, extra):
        seller = self.request.user
        return Listing.objects.filter(
            posted_by_role=Listing.PostedByRole.BUYER_REQUEST,
        ).filter(extra).select_related("category").prefetch_related(
            "skus", "bids", "bids__price_tiers",
        ).annotate(
            bid_count=Count("bids", distinct=True),
            my_bid_count=Count("bids", filter=Q(bids__bidder=seller), distinct=True),
        ).distinct()

    def get_queryset(self):
        seller = self.request.user
        if self.action == "mine":
            mine = Q(bids__bidder=seller)
            if self.request.query_params.get("won") in ("true", "1"):
                mine &= Q(bids__status__in=(Bid.Status.ACCEPTED, Bid.Status.COMPLETED))
            return self._scoped(mine)
        if self.action == "retrieve":
            return self._scoped(Q(status=Listing.Status.OPEN_FOR_BIDDING) | Q(bids__bidder=seller))
        return self._scoped(Q(status=Listing.Status.OPEN_FOR_BIDDING))

    @action(detail=False, methods=["get"])
    def mine(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


# ------------------------------------------------------------------ lookups


class _LookupViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsActiveVerifiedSellerActor]
    pagination_class = LargeListPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]


class SellerCategoryLookupViewSet(_LookupViewSet):
    """Active categories. Filter by `type` (product | service) and `parent`."""

    queryset = Category.objects.filter(status=Category.Status.ACTIVE)
    serializer_class = SellerCategoryLookupSerializer
    filterset_fields = ["type", "parent"]
    search_fields = ["name", "name_bn"]


class SellerBrandLookupViewSet(_LookupViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = SellerBrandLookupSerializer
    search_fields = ["name"]


class SellerMeasurementLookupViewSet(_LookupViewSet):
    queryset = Measurement.objects.all()
    serializer_class = SellerMeasurementLookupSerializer
    search_fields = ["name", "symbol"]


class SellerAttributeLookupViewSet(_LookupViewSet):
    """Active attributes (Size, Colour...) with their active values, for the SKU options."""

    queryset = Attribute.objects.filter(is_active=True).prefetch_related("values")
    serializer_class = SellerAttributeLookupSerializer
    search_fields = ["name", "name_bn"]
