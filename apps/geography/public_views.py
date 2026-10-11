"""
Public, read-only geography lists — for screens that run before anyone is
logged in (the seller sign-up form's country / state / city / thana
dropdowns).

Deliberately a separate set of endpoints from the admin geography API
(`/api/v1/geography/`), not a loosened version of it: those rows carry audit
columns (who created or edited each row, by name) that must not be public,
and they accept writes. These return only what a dropdown needs, and only GET.

`authentication_classes = []` so a stale or expired token in the browser can
never turn a public read into a 401.
"""

from rest_framework import mixins, serializers, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny

from .models import City, Country, State, Thana


class PublicGeographyPagination(LimitOffsetPagination):
    """A dropdown needs the whole list, so the page is much larger than the
    admin lists (default 500, max 1000). Still capped."""

    default_limit = 500
    max_limit = 1000


class PublicCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "slug", "country_code", "flag_url"]


class PublicStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "slug", "country"]


class PublicCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug", "country", "state"]


class PublicThanaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thana
        fields = ["id", "name", "slug", "country", "state", "city"]


class PublicGeographyViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = PublicGeographyPagination
    search_fields = ["name"]


class PublicCountryViewSet(PublicGeographyViewSet):
    queryset = Country.objects.all()
    serializer_class = PublicCountrySerializer


class PublicStateViewSet(PublicGeographyViewSet):
    queryset = State.objects.all()
    serializer_class = PublicStateSerializer
    filterset_fields = ["country"]


class PublicCityViewSet(PublicGeographyViewSet):
    queryset = City.objects.all()
    serializer_class = PublicCitySerializer
    filterset_fields = ["country", "state"]


class PublicThanaViewSet(PublicGeographyViewSet):
    queryset = Thana.objects.all()
    serializer_class = PublicThanaSerializer
    filterset_fields = ["country", "state", "city"]
