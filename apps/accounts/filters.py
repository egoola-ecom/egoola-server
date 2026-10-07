import django_filters

from .models import User


class BuyerFilter(django_filters.FilterSet):
    """Buyer list filters. `email_verified` / `phone_verified` are true/false
    flags over the *_verified_at timestamps; `created_from` / `created_to`
    are inclusive dates (YYYY-MM-DD) on the signup date."""

    email_verified = django_filters.BooleanFilter(field_name="email_verified_at", lookup_expr="isnull", exclude=True)
    phone_verified = django_filters.BooleanFilter(field_name="phone_verified_at", lookup_expr="isnull", exclude=True)
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = User
        fields = ["status", "country", "state", "city", "thana"]
