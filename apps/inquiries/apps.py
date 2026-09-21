from django.apps import AppConfig


class InquiriesConfig(AppConfig):
    """Buyer inquiries / quote requests (Section 3.8)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inquiries"
    label = "inquiries"
