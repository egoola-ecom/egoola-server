from django.contrib import admin

from .models import Bid


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "bidder", "price_type", "price", "hourly_rate", "status")
    list_filter = ("price_type", "status")
