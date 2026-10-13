"""
The seller's own listing endpoints (`/api/v1/seller/listings/` for products,
`/api/v1/seller/gigs/` for gigs) and the read-only
lookups a seller needs to fill the listing form (`/api/v1/seller/lookups/...`).

Only a seller who can operate (verified AND active) may use them — see
IsActiveVerifiedSellerActor. A seller sees and changes only their own
listings. There is no delete: only an admin can delete a listing.
"""

from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from django_filters.rest_framework import DjangoFilterBackend

from apps.authentication.permissions import IsActiveVerifiedSellerActor
from apps.core.mixins import AuditedViewSetMixin
from apps.core.pagination import LargeListPagination

from .filters import SellerGigFilter, SellerListingFilter
from .models import Attribute, AttributeValue, Brand, Category, Listing, Measurement
from .serializers import (
    SellerGigListSerializer,
    SellerGigSerializer,
    SellerListingListSerializer,
    SellerListingSerializer,
)
from .thumbnail import ThumbnailViewSetMixin


class _SellerListingBaseViewSet(
    ThumbnailViewSetMixin,
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
    `approved` or `pending` listing keeps its status. The thumbnail has its own
    endpoint and follows the same rule. See SellerListingMixin."""

    permission_classes = [IsActiveVerifiedSellerActor]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ["created_at", "updated_at", "requested_at", "title", "status", "id"]
    ordering = ["-created_at", "-id"]
    thumbnail_resubmits = True

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
        if self.action in ("update", "partial_update", "thumbnail"):
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


# ------------------------------------------------------------------ lookups


class _LookupViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsActiveVerifiedSellerActor]
    pagination_class = LargeListPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]


class SellerCategoryLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "type", "parent", "name", "name_bn", "slug", "sort_order"]


class SellerCategoryLookupViewSet(_LookupViewSet):
    """Active categories. Filter by `type` (product | service) and `parent`."""

    queryset = Category.objects.filter(status=Category.Status.ACTIVE)
    serializer_class = SellerCategoryLookupSerializer
    filterset_fields = ["type", "parent"]
    search_fields = ["name", "name_bn"]


class SellerBrandLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug"]


class SellerBrandLookupViewSet(_LookupViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = SellerBrandLookupSerializer
    search_fields = ["name"]


class SellerMeasurementLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ["id", "name", "slug", "symbol"]


class SellerMeasurementLookupViewSet(_LookupViewSet):
    queryset = Measurement.objects.all()
    serializer_class = SellerMeasurementLookupSerializer
    search_fields = ["name", "symbol"]


class SellerAttributeValueLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ["id", "name", "name_bn"]


class SellerAttributeLookupSerializer(serializers.ModelSerializer):
    values = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = ["id", "name", "name_bn", "values"]

    def get_values(self, attribute):
        active = [value for value in attribute.values.all() if value.is_active]
        return SellerAttributeValueLookupSerializer(active, many=True).data


class SellerAttributeLookupViewSet(_LookupViewSet):
    """Active attributes (Size, Colour...) with their active values, for the SKU options."""

    queryset = Attribute.objects.filter(is_active=True).prefetch_related("values")
    serializer_class = SellerAttributeLookupSerializer
    search_fields = ["name", "name_bn"]
