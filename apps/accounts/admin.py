from django.contrib import admin

from .models import Admin, AdminMedia, BuyerMedia, Seller, SellerInfo, SellerMedia, User


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "type", "status")
    list_filter = ("type", "status")
    search_fields = ("name", "email", "mobile")


@admin.register(AdminMedia)
class AdminMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "admin", "media_type", "media_for")
    list_filter = ("media_type", "media_for")


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "verification_status", "status", "wallet_balance")
    list_filter = ("verification_status", "status")
    search_fields = ("name", "email", "phone")


@admin.register(SellerMedia)
class SellerMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "seller", "media_type", "media_for")
    list_filter = ("media_type", "media_for")


@admin.register(SellerInfo)
class SellerInfoAdmin(admin.ModelAdmin):
    list_display = ("id", "seller", "business_type", "owner_name")
    search_fields = ("business_type", "owner_name")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "status", "wallet_balance")
    list_filter = ("status",)
    search_fields = ("name", "email", "phone")


@admin.register(BuyerMedia)
class BuyerMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "media_type", "media_for")
    list_filter = ("media_type", "media_for")
