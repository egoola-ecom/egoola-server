"""
The admin bid panel (`/api/v1/bidding/bids/...`): oversight of every bid,
plus "do everything" — create/edit a bid on any seller's behalf, accept one
on the buyer's behalf, or undo a hire. See admin_api/serializers.py and
services.py for the rules. No delete — a bid is never hard-deleted, only
its status changes.
"""

import django_filters
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminActor
from apps.catalog.models import Listing
from apps.core.pagination import DefaultCursorPagination

from ..models import Bid
from ..services import accept_bid, admin_reject_accepted_bid
from .serializers import AdminBidDetailSerializer, AdminBidListSerializer, AdminBidWriteSerializer


class AdminBidFilter(django_filters.FilterSet):
    class Meta:
        model = Bid
        fields = ["status", "listing", "bidder"]


class AdminBidViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminActor]
    pagination_class = DefaultCursorPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = AdminBidFilter
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        if self.action == "list":
            return AdminBidListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AdminBidWriteSerializer
        return AdminBidDetailSerializer

    def get_queryset(self):
        queryset = Bid.objects.select_related("listing", "bidder").prefetch_related("price_tiers")
        if self.action in ("update", "partial_update"):
            return queryset.select_for_update(of=("self",))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bid = serializer.save()
        detail = Bid.objects.select_related("listing", "bidder").prefetch_related("price_tiers").get(pk=bid.pk)
        return Response(AdminBidDetailSerializer(detail, context=self.get_serializer_context()).data, status=201)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            bid_id = instance.pk
        bid = Bid.objects.select_related("listing", "bidder").prefetch_related("price_tiers").get(pk=bid_id)
        return Response(AdminBidDetailSerializer(bid, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """`POST /bidding/bids/{id}/accept/` — hire this bidder on the
        buyer's behalf. Body: `{"price_tier_id": <id>}`, required only when
        the bid quoted more than one price tier."""
        with transaction.atomic():
            bid = get_object_or_404(Bid, pk=pk)
            job = Listing.all_objects.select_for_update(of=("self",)).get(pk=bid.listing_id)
            if job.status != Listing.Status.OPEN_FOR_BIDDING:
                return Response({"detail": "This job isn't open for bidding."}, status=status.HTTP_400_BAD_REQUEST)
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
            "bid": AdminBidDetailSerializer(bid, context=self.get_serializer_context()).data,
            "order": {"id": order.id, "status": order.status, "payable": str(order.payable)},
        })

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """`POST /bidding/bids/{id}/reject/` — undo an already-accepted hire
        (not a full job cancel): this bid goes to `rejected`, its Order is
        cancelled, and the job reopens for bidding. Every other bid that
        auto-rejected when this one was accepted stays `rejected`. Body:
        `{"note": "..."}` (required)."""
        note = (request.data.get("note") or "").strip()
        if not note:
            return Response({"note": "A reason is required."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            bid = get_object_or_404(Bid.objects.select_for_update(of=("self",)), pk=pk)
            if bid.status != Bid.Status.ACCEPTED:
                return Response({"detail": "Only an accepted bid can be rejected this way."}, status=status.HTTP_400_BAD_REQUEST)
            bid = admin_reject_accepted_bid(bid, request.user, note)
        return Response(AdminBidDetailSerializer(bid, context=self.get_serializer_context()).data)
