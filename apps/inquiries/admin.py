from django.contrib import admin

from .models import QuoteRequest


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "buyer", "seller", "qty", "status")
    list_filter = ("status",)
