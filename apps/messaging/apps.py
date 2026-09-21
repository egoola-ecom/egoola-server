from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """Chat messages between buyers and sellers (Section 3.9)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messaging"
    label = "messaging"
