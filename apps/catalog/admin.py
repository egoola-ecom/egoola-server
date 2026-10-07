from django.contrib import admin

from .models import Brand, Category, Listing, ListingMedia, ListingPriceTier, ListingStatusChangeLog, Measurement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "parent", "sort_order", "status")
    list_filter = ("type", "status")
    search_fields = ("name", "name_bn", "slug")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "creator_name")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "symbol")
    search_fields = ("name", "slug", "symbol")


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


@admin.register(ListingStatusChangeLog)
class ListingStatusChangeLogAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "status", "creator_type", "creator_name", "created_at")
    list_filter = ("status", "creator_type")
    search_fields = ("listing__title", "creator_name")
