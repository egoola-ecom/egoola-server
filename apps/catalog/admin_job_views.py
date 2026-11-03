"""
The admin job panel (`/api/v1/catalog/jobs/...`): every buyer's job request,
admin oversight plus "do everything" — create or edit a job on any buyer's
behalf. See admin_job_serializers.py for the state machine. No delete — a
job is cancelled, never removed (see Listing.Status).
"""

from django.db import transaction
from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminActor

from .admin_job_serializers import AdminJobDetailSerializer, AdminJobListSerializer, AdminJobWriteSerializer
from .filters import ListingFilter
from .models import Listing, ListingSku


class AdminJobViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminActor]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ListingFilter
    search_fields = ["title", "title_bn", "description", "buyer__name", "buyer__phone"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["-created_at", "-id"]

    def get_serializer_class(self):
        if self.action == "list":
            return AdminJobListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AdminJobWriteSerializer
        return AdminJobDetailSerializer

    def _base_queryset(self):
        return Listing.all_objects.filter(posted_by_role=Listing.PostedByRole.BUYER_REQUEST)

    def _detail_queryset(self):
        return self._base_queryset().select_related(
            "category", "buyer", "country", "state", "city", "thana",
        ).prefetch_related("skus", "bids", "bids__accepted_price_tier").annotate(bid_count=Count("bids"))

    def get_queryset(self):
        if self.action == "list":
            return self._base_queryset().select_related("category", "buyer").prefetch_related(
                Prefetch("skus", queryset=ListingSku.objects.filter(is_active=True)),
            ).annotate(bid_count=Count("bids"))
        if self.action in ("update", "partial_update"):
            return self._base_queryset().select_for_update(of=("self",))
        return self._detail_queryset()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        detail = self._detail_queryset().get(pk=job.pk)
        return Response(AdminJobDetailSerializer(detail, context=self.get_serializer_context()).data, status=201)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            job_id = instance.pk
        detail = self._detail_queryset().get(pk=job_id)
        return Response(AdminJobDetailSerializer(detail, context=self.get_serializer_context()).data)
