from django.apps import AppConfig


class BiddingConfig(AppConfig):
    """Bidding on jobs and services (Section 3.6 of the DB Redesign document)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bidding"
    label = "bidding"
