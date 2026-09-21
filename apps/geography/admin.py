from django.contrib import admin

from .models import City, Country, State, Thana


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "country_code")
    search_fields = ("name", "slug")


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "country", "state_code")
    list_filter = ("country",)
    search_fields = ("name", "slug")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "state", "country", "city_code")
    list_filter = ("country", "state")
    search_fields = ("name", "slug")


@admin.register(Thana)
class ThanaAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "city", "state", "country", "thana_code")
    list_filter = ("country", "state", "city")
    search_fields = ("name", "slug")
