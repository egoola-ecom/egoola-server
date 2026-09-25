from rest_framework import mixins, viewsets

from apps.authentication.permissions import IsAdminActor
from apps.core.mixins import AuditedViewSetMixin

from .models import City, Country, State, Thana
from .serializers import (
    CityListSerializer,
    CitySerializer,
    CountrySerializer,
    StateListSerializer,
    StateSerializer,
    ThanaListSerializer,
    ThanaSerializer,
)


class CountryViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (search by name),
    Delete. No retrieve: the client never needs a single country's detail
    on its own."""

    permission_classes = [IsAdminActor]
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    search_fields = ["name"]


class StateViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (filter by
    country, search by name), Delete. No retrieve, same as CountryViewSet."""

    permission_classes = [IsAdminActor]
    queryset = State.objects.select_related("country").all()
    serializer_class = StateSerializer
    filterset_fields = ["country"]
    search_fields = ["name"]

    def get_serializer_class(self):
        return StateListSerializer if self.action == "list" else StateSerializer


class CityViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (filter by
    country/state, search by name), Delete. No retrieve, same as
    CountryViewSet."""

    permission_classes = [IsAdminActor]
    queryset = City.objects.select_related("country", "state").all()
    serializer_class = CitySerializer
    filterset_fields = ["country", "state"]
    search_fields = ["name"]

    def get_serializer_class(self):
        return CityListSerializer if self.action == "list" else CitySerializer


class ThanaViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (filter by
    country/state/city, search by name), Delete. No retrieve, same as
    CountryViewSet."""

    permission_classes = [IsAdminActor]
    queryset = Thana.objects.select_related("country", "state", "city").all()
    serializer_class = ThanaSerializer
    filterset_fields = ["country", "state", "city"]
    search_fields = ["name"]

    def get_serializer_class(self):
        return ThanaListSerializer if self.action == "list" else ThanaSerializer
