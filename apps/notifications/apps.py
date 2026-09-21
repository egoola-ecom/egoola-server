from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Notifications sent to users (Section 3.11)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
