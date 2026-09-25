from django.contrib import admin

from .models import Favourite, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "reviewer", "listing", "rating")
    list_filter = ("rating",)


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "listing")
