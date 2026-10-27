from django.contrib import admin

from .models import Bid, BidPriceTier


class BidPriceTierInline(admin.TabularInline):
    model = BidPriceTier
    extra = 0


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "bidder", "status", "accepted_price_tier")
    list_filter = ("status",)
    inlines = [BidPriceTierInline]
