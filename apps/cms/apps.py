from django.apps import AppConfig


class CmsConfig(AppConfig):
    """Site content and settings that admins manage (Section 3.12)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cms"
    label = "cms"
