"""
A buyer looking at the bids on their own job
(`/api/v1/buyer/jobs/{job_id}/bids/`). Read-only — accepting a bid is a
later step. See docs/buyer-api-guide.md.
"""

from django.shortcuts import get_object_or_404
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView

from apps.authentication.permissions import IsBuyerActor
from apps.catalog.models import Listing
from apps.core.pagination import BuyerPagePagination

from .buyer_serializers import BuyerBidSerializer
from .models import Bid


class BuyerJobBidListView(ListAPIView):
    """Every bid placed on one of my jobs — whatever its status (pending,
    accepted, rejected, cancelled, completed), so a buyer can see the full
    history, not just what's currently live."""

    permission_classes = [IsBuyerActor]
    pagination_class = BuyerPagePagination
    serializer_class = BuyerBidSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        job = get_object_or_404(
            Listing.all_objects, pk=self.kwargs["job_id"], buyer=self.request.user,
            posted_by_role=Listing.PostedByRole.BUYER_REQUEST,
        )
        queryset = Bid.objects.filter(listing=job).select_related("bidder").prefetch_related(
            "price_tiers", "accepted_price_tier",
        )
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset
