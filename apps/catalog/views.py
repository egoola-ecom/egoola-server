from rest_framework import mixins, viewsets

from apps.authentication.permissions import IsAdminActor
from apps.core.mixins import AuditedViewSetMixin

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (filter by type/
    status, search by name), Delete. No retrieve, same as the Geography
    viewsets."""

    permission_classes = [IsAdminActor]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ["type", "status"]
    search_fields = ["name"]
