import django_filters
from django.db.models import Exists, OuterRef

from .models import Cart, CartItem


class CartFilter(django_filters.FilterSet):
    """Admin cart list filters.

    - `buyer`: exact buyer id.
    - `cart_type`, `is_active`: exact.
    - `has_order`: true/false — whether this cart has already become an order.
    - `listing`: only carts that hold this listing id (any line).
    - `created_from` / `created_to`: inclusive dates (YYYY-MM-DD).
    """

    has_order = django_filters.BooleanFilter(field_name="order", lookup_expr="isnull", exclude=True)
    listing = django_filters.NumberFilter(method="filter_listing")
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Cart
        fields = ["buyer", "cart_type", "is_active"]

    def filter_listing(self, queryset, name, value):
        return queryset.filter(Exists(CartItem.objects.filter(cart=OuterRef("pk"), listing_id=value)))
