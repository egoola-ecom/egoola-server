from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Orders, order items, shopping carts, addresses, and payments (Section 3.7)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"
