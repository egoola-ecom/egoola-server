from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "notifiable_type", "notifiable_id", "read_at", "created_at")
    list_filter = ("type", "notifiable_type")
