from django.contrib import admin

from .models import Category, Listing, ListingMedia, ListingPriceTier, Measurement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "parent", "sort_order", "status")
    list_filter = ("type", "status")
    search_fields = ("name", "name_bn", "slug")


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "symbol")
    search_fields = ("name", "symbol")


class ListingPriceTierInline(admin.TabularInline):
    model = ListingPriceTier
    extra = 0


class ListingMediaInline(admin.TabularInline):
    model = ListingMedia
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "catalog_type", "listing_type", "seller", "buyer", "price", "status")
    list_filter = ("catalog_type", "listing_type", "status")
    search_fields = ("title", "slug", "description")
    inlines = [ListingPriceTierInline, ListingMediaInline]
