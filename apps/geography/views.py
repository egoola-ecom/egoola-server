from rest_framework.viewsets import ModelViewSet

from .models import City, Country, State, Thana
from .serializers import CitySerializer, CountrySerializer, StateSerializer, ThanaSerializer


class CountryViewSet(ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    filterset_fields = ["country_code"]
    search_fields = ["name", "slug"]


class StateViewSet(ModelViewSet):
    queryset = State.objects.select_related("country").all()
    serializer_class = StateSerializer
    filterset_fields = ["country"]
    search_fields = ["name", "slug"]


class CityViewSet(ModelViewSet):
    queryset = City.objects.select_related("country", "state").all()
    serializer_class = CitySerializer
    filterset_fields = ["country", "state"]
    search_fields = ["name", "slug"]


class ThanaViewSet(ModelViewSet):
    queryset = Thana.objects.select_related("country", "state", "city").all()
    serializer_class = ThanaSerializer
    filterset_fields = ["country", "state", "city"]
    search_fields = ["name", "slug"]
