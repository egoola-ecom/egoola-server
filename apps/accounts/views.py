from rest_framework.viewsets import ModelViewSet

from apps.authentication.permissions import IsAdminActor

from .models import Admin, Seller, User
from .serializers import (
    AdminListSerializer,
    AdminSerializer,
    BuyerListSerializer,
    SellerListSerializer,
    SellerSerializer,
    UserSerializer,
)


class AdminViewSet(ModelViewSet):
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


class SellerViewSet(ModelViewSet):
    """Seller Management. Media and the business-info profile are handled
    through this same API (see SellerSerializer) — there's no separate
    /sellers/{id}/media/ or /sellers/{id}/info/ endpoint."""

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
        ).prefetch_related("media")


class BuyerViewSet(ModelViewSet):
    """Buyer management — model is `User` (see models.py docstring). Media
    is handled through this same API (see UserSerializer) — there's no
    separate /buyers/{id}/media/ endpoint."""

    permission_classes = [IsAdminActor]
    filterset_fields = ["status"]
    search_fields = ["name", "email", "phone"]

    def get_serializer_class(self):
        return BuyerListSerializer if self.action == "list" else UserSerializer

    def get_queryset(self):
        if self.action == "list":
            return User.objects.all()
        return User.objects.select_related("country", "state", "city", "thana").prefetch_related("media")
