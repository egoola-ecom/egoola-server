from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Admin Dashboard summary (PRD: admin-dashboard-prd.md). No models of its
    own — it only aggregates other apps' tables into one read-only endpoint."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    label = "dashboard"
