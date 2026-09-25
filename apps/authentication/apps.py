from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Login and JWT handling for all three actor tables (Admin/Seller/
    Buyer) — kept separate from `accounts` (which owns the Admin/Seller/
    Buyer *management* CRUD) so "how do you prove who you are" and "how is
    your record shaped/edited" aren't mixed into one app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    label = "authentication"
