from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Categories, and the product/service catalog (Section 3.4, 3.5 of the DB Redesign document)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    label = "catalog"
