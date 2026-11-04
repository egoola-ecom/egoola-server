"""
Seller's job board (`/api/v1/seller/jobs/...`): browse open jobs, see one in
full (with my own bids on it), and "jobs I've bid on". See
docs/buyer/buyer-api-guide.md / seller-api-guide.md for the full contract. Bidding
itself is apps.bidding.seller.views.
"""

from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter

from apps.authentication.permissions import IsActiveVerifiedSellerActor
from apps.bidding.models import Bid
from apps.core.pagination import DefaultCursorPagination

from .filters import SellerJobFilter
from .models import Listing
from .seller_job_serializers import SellerJobDetailSerializer, SellerJobListSerializer


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
