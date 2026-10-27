"""
A buyer's own job postings (`/api/v1/buyer/jobs/...`). See
docs/buyer-api-guide.md and buyer_job_serializers.py for the state machine.
"""

from django.db import transaction
from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.authentication.permissions import IsBuyerActor
from apps.core.pagination import BuyerPagePagination

from .buyer_job_serializers import BuyerJobDetailSerializer, BuyerJobListSerializer, BuyerJobWriteSerializer
from .models import Listing, ListingSku


class BuyerJobViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """My own jobs: create, list, see, edit. No delete — a job is cancelled,
    never removed (see Listing.Status)."""

    permission_classes = [IsBuyerActor]
    pagination_class = BuyerPagePagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["title", "title_bn", "description"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        if self.action == "list":
            return BuyerJobListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BuyerJobWriteSerializer
        return BuyerJobDetailSerializer

    def _base_queryset(self):
        return Listing.all_objects.filter(
            buyer=self.request.user, posted_by_role=Listing.PostedByRole.BUYER_REQUEST,
        )

    def _detail_queryset(self):
        """The rich, unlocked shape BuyerJobDetailSerializer needs — used for
        a plain GET and for the response after create/update (never for the
        locked row update() itself fetches and saves)."""
        return self._base_queryset().select_related(
            "category", "country", "state", "city", "thana",
        ).prefetch_related("skus", "bids", "bids__accepted_price_tier").annotate(bid_count=Count("bids"))

    def get_queryset(self):
        if self.action == "list":
            return self._base_queryset().select_related("category").prefetch_related(
                Prefetch("skus", queryset=ListingSku.objects.filter(is_active=True)),
            ).annotate(bid_count=Count("bids"))
        if self.action in ("update", "partial_update"):
            # Locks the row for the whole save, same as the seller's own listing edit.
            return self._base_queryset().select_for_update(of=("self",))
        return self._detail_queryset()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        detail = self._detail_queryset().get(pk=job.pk)
        return Response(BuyerJobDetailSerializer(detail, context=self.get_serializer_context()).data, status=201)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            job_id = instance.pk
        detail = self._detail_queryset().get(pk=job_id)
        return Response(BuyerJobDetailSerializer(detail, context=self.get_serializer_context()).data)
