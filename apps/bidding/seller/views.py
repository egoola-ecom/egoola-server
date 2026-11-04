"""
A seller's own bids (`/api/v1/seller/jobs/{job_id}/bids/` to place one,
`/api/v1/seller/bids/...` to manage them). See seller/serializers.py for the
lifecycle rules.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from apps.authentication.permissions import IsActiveVerifiedSellerActor
from apps.catalog.models import Listing
from apps.core.pagination import DefaultCursorPagination

from ..models import Bid
from .filters import SellerBidFilter
from .serializers import SellerBidDetailSerializer, SellerBidListSerializer, SellerBidWriteSerializer


def _detail_queryset():
    return Bid.objects.select_related("listing").prefetch_related("price_tiers")


class SellerJobBidCreateView(CreateAPIView):
    """`POST /seller/jobs/{job_id}/bids/` — place a bid on an open job."""

    permission_classes = [IsActiveVerifiedSellerActor]
    serializer_class = SellerBidWriteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["job"] = get_object_or_404(
            Listing.objects, pk=self.kwargs["job_id"], posted_by_role=Listing.PostedByRole.BUYER_REQUEST,
        )
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bid = serializer.save()
        detail = _detail_queryset().get(pk=bid.pk)
        return Response(SellerBidDetailSerializer(detail).data, status=201)


class SellerBidViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """My own bids, across every job: list (cursor, with job details
    embedded), see one, edit while pending (price tiers reconciled like a
    listing's SKUs), or cancel (`status: cancelled`). No delete — never
    hard-deleted, only its status changes."""

    permission_classes = [IsActiveVerifiedSellerActor]
    pagination_class = DefaultCursorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SellerBidFilter
    search_fields = ["listing__title"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        if self.action == "list":
            return SellerBidListSerializer
        if self.action in ("update", "partial_update"):
            return SellerBidWriteSerializer
        return SellerBidDetailSerializer

    def _base_queryset(self):
        return Bid.objects.filter(bidder=self.request.user)

    def get_queryset(self):
        if self.action in ("update", "partial_update"):
            return self._base_queryset().select_for_update(of=("self",))
        return self._base_queryset().select_related("listing").prefetch_related("price_tiers")

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            bid_id = instance.pk
        detail = _detail_queryset().get(pk=bid_id)
        return Response(SellerBidDetailSerializer(detail).data)
