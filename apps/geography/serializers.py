from rest_framework import serializers

from .models import City, Country, State, Thana


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "slug", "country_code", "flag_path", "flag_url"]


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "country", "name", "slug", "state_code", "flag_path", "flag_url"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "country", "state", "name", "slug", "city_code", "flag_path", "flag_url"]


class ThanaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thana
        fields = [
            "id",
            "country",
            "state",
            "city",
            "name",
            "slug",
            "thana_code",
            "flag_path",
            "flag_url",
        ]
