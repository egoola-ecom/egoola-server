"""
A buyer looking at, and acting on, the bids on their own job
(`/api/v1/buyer/jobs/{job_id}/bids/...`). See docs/buyer/buyer-api-guide.md.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsBuyerActor
from apps.catalog.models import Listing
from apps.core.pagination import BuyerPagePagination

from ..models import Bid
from ..services import accept_bid
from .serializers import BuyerBidSerializer


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


class BuyerBidAcceptView(APIView):
    """`POST /buyer/jobs/{job_id}/bids/{bid_id}/accept/` — hire this bidder.
    Every other pending bid on the job is auto-rejected, the job moves to
    `in_progress`, and an Order is created directly (no cart). Body:
    `{"price_tier_id": <id>}` — required only when the bid quoted more than
    one price tier; with a single tier, it's picked automatically."""

    permission_classes = [IsBuyerActor]

    def post(self, request, job_id, bid_id):
        with transaction.atomic():
            job = get_object_or_404(
                Listing.all_objects.select_for_update(of=("self",)),
                pk=job_id, buyer=request.user, posted_by_role=Listing.PostedByRole.BUYER_REQUEST,
            )
            if job.status != Listing.Status.OPEN_FOR_BIDDING:
                return Response({"detail": "This job isn't open for bidding."}, status=status.HTTP_400_BAD_REQUEST)

            bid = get_object_or_404(Bid, pk=bid_id, listing=job)
            if bid.status != Bid.Status.PENDING:
                return Response({"detail": "Only a pending bid can be accepted."}, status=status.HTTP_400_BAD_REQUEST)

            tiers = list(bid.price_tiers.all())
            tier_id = request.data.get("price_tier_id")
            if tier_id is not None:
                tier = next((t for t in tiers if t.id == tier_id), None)
                if tier is None:
                    return Response({"price_tier_id": "Doesn't belong to this bid."}, status=status.HTTP_400_BAD_REQUEST)
            elif len(tiers) == 1:
                tier = tiers[0]
            else:
                return Response(
                    {"price_tier_id": "This bid has more than one price option — say which one you're accepting."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bid, order = accept_bid(job, bid, tier, request.user)

        return Response({
            "bid": BuyerBidSerializer(bid).data,
            "order": {"id": order.id, "status": order.status, "payable": str(order.payable)},
        })
