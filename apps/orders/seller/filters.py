import django_filters

from ..models import Order


class SellerOrderFilter(django_filters.FilterSet):
    """A seller's own order list filters: `status` exact, `created_from`/
    `created_to` inclusive dates (YYYY-MM-DD)."""

    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Order
        fields = ["status"]
