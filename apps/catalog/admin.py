from django.contrib import admin

from .models import (
    Attribute,
    AttributeValue,
    Brand,
    Category,
    Listing,
    ListingMedia,
    ListingPriceTier,
    ListingSku,
    ListingSkuVariant,
    ListingInfoChangeLog,
    ListingStatusChangeLog,
    Measurement,
)


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


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 0


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "name_bn", "is_active", "creator_name")
    list_filter = ("is_active",)
    search_fields = ("name", "name_bn")
    inlines = [AttributeValueInline]


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ("id", "attribute", "name", "name_bn", "is_active")
    list_filter = ("is_active", "attribute")
    search_fields = ("name", "name_bn")


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "symbol")
    search_fields = ("name", "slug", "symbol")


class ListingPriceTierInline(admin.TabularInline):
    model = ListingPriceTier
    extra = 0


class ListingSkuInline(admin.TabularInline):
    model = ListingSku
    extra = 0
    show_change_link = True


class ListingSkuVariantInline(admin.TabularInline):
    model = ListingSkuVariant
    extra = 0


@admin.register(ListingSku)
class ListingSkuAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "sku", "price", "discounted_price", "stock_qty", "is_active")
    list_filter = ("is_active",)
    search_fields = ("sku", "listing__title")
    inlines = [ListingSkuVariantInline]


class ListingMediaInline(admin.TabularInline):
    model = ListingMedia
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "catalog_type", "listing_type", "seller", "buyer", "status")
    list_filter = ("catalog_type", "listing_type", "status")
    search_fields = ("title", "slug", "description")
    inlines = [ListingSkuInline, ListingPriceTierInline, ListingMediaInline]


@admin.register(ListingStatusChangeLog)
class ListingStatusChangeLogAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "status", "creator_type", "creator_name", "created_at")
    list_filter = ("status", "creator_type")
    search_fields = ("listing__title", "creator_name")


@admin.register(ListingInfoChangeLog)
class ListingInfoChangeLogAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "changed_fields", "creator_type", "creator_name", "created_at")
    list_filter = ("creator_type",)
    search_fields = ("listing__title", "creator_name")
