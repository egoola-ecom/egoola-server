from django.apps import AppConfig


class GeographyConfig(AppConfig):
    """Geography reference data — Section 3.1 of the DB Redesign document."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.geography"
    label = "geography"
