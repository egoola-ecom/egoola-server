from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.authentication.permissions import IsAdminActor, IsSuperAdminActor
from apps.core.mixins import AuditedViewSetMixin
from apps.core.pagination import DefaultCursorPagination

from .filters import BuyerFilter, SellerFilter
from .models import Admin, Seller, User
from .serializers import (
    AdminListSerializer,
    AdminSerializer,
    BuyerListSerializer,
    SellerListSerializer,
    SellerSerializer,
    UserSerializer,
)


class AdminViewSet(AuditedViewSetMixin, ModelViewSet):
    """Admin Management. Media is handled through this same API (see
    AdminSerializer) — there's no separate /admins/{id}/media/ endpoint.

    Super-admin only (IsSuperAdminActor): a plain `admin` token gets 403
    here, though it can still use Seller/Buyer/Listing management. A
    super-admin can't delete themselves, and AdminSerializer stops them
    changing their own type or status — together that means there is
    always at least one active super-admin left."""

    permission_classes = [IsSuperAdminActor]
    filterset_fields = ["type", "status"]
    search_fields = ["name", "email", "mobile"]

    def destroy(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            return Response(
                {"detail": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    def get_serializer_class(self):
        return AdminListSerializer if self.action == "list" else AdminSerializer

    def get_queryset(self):
        if self.action == "list":
            return Admin.objects.all()
        return Admin.objects.select_related("country", "state", "city", "thana").prefetch_related("media")


class SellerViewSet(AuditedViewSetMixin, ModelViewSet):
    """Seller Management. Media and the business-info profile are handled
    through this same API (see SellerSerializer) — there's no separate
    /sellers/{id}/media/ or /sellers/{id}/info/ endpoint.

    AuditedViewSetMixin is required here, not just convention: SellerSerializer
    reads creator_type/updater_type off validated_data to decide the
    default verification_status on create and to attribute each
    SellerVerificationLog row to the actor who wrote it.

    `GET /sellers/requests/` is the "Seller Request" queue: only sellers who
    registered by themselves and have not been acted on yet
    (is_seller_request = true), with cursor pagination. Filters: see SellerFilter."""

    permission_classes = [IsAdminActor]
    filterset_class = SellerFilter
    search_fields = ["name", "email", "phone"]
    # Used only by the request queue's OrderingFilter (below).
    ordering_fields = ["requested_at", "created_at", "name", "id"]
    ordering = ["-requested_at", "-id"]

    def get_serializer_class(self):
        return SellerListSerializer if self.action in ("list", "seller_requests") else SellerSerializer

    def get_queryset(self):
        if self.action == "list":
            return Seller.objects.all()
        if self.action == "seller_requests":
            return Seller.objects.filter(is_seller_request=True)
        return Seller.objects.select_related(
            "country", "state", "city", "thana", "info"
        ).prefetch_related("media", "verification_logs", "profile_change_logs")

    @action(
        detail=False,
        methods=["get"],
        url_path="requests",
        pagination_class=DefaultCursorPagination,
        filter_backends=[DjangoFilterBackend, SearchFilter, OrderingFilter],
    )
    def seller_requests(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class BuyerViewSet(AuditedViewSetMixin, ModelViewSet):
    """Buyer management — model is `User` (see models.py docstring). Media
    is handled through this same API (see UserSerializer) — there's no
    separate /buyers/{id}/media/ endpoint. Filters: see BuyerFilter."""

    permission_classes = [IsAdminActor]
    filterset_class = BuyerFilter
    search_fields = ["name", "email", "phone"]

    def get_serializer_class(self):
        return BuyerListSerializer if self.action == "list" else UserSerializer

    def get_queryset(self):
        if self.action == "list":
            return User.objects.all()
        return User.objects.select_related("country", "state", "city", "thana").prefetch_related("media")
