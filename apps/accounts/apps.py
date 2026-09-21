from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Identity and login, plus the seller's business profile (Section 3.2, 3.3 of the DB Redesign document)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
