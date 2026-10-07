from rest_framework.viewsets import ModelViewSet

from apps.authentication.permissions import IsAdminActor
from apps.core.mixins import AuditedViewSetMixin

from .filters import BuyerFilter
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

    Admin-only (IsAdminActor) — Seller/Buyer actors can't manage Admins,
    Sellers or Buyers yet; that's the current phase's scope, not a
    permanent rule."""

    permission_classes = [IsAdminActor]
    filterset_fields = ["type", "status"]
    search_fields = ["name", "email", "mobile"]

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
    SellerVerificationLog row to the actor who wrote it."""

    permission_classes = [IsAdminActor]
    filterset_fields = ["verification_status", "status"]
    search_fields = ["name", "email", "phone"]

    def get_serializer_class(self):
        return SellerListSerializer if self.action == "list" else SellerSerializer

    def get_queryset(self):
        if self.action == "list":
            return Seller.objects.all()
        return Seller.objects.select_related(
            "country", "state", "city", "thana", "info"
        ).prefetch_related("media", "verification_logs")


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
