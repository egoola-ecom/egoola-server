from django.contrib import admin

from .models import Banner, EmailTemplate, Setting


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "placement", "heading", "status", "sort_order", "starts_at", "ends_at")
    list_filter = ("placement", "status")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "subject", "is_active")
    list_filter = ("is_active",)
    search_fields = ("key", "subject")


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)
