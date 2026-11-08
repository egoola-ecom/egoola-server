import django_filters
from django.utils import timezone

from ..models import Listing, ListingSku


class _ListingDateFilters(django_filters.FilterSet):
    """Shared date filters (inclusive, YYYY-MM-DD): `created_*` is the creation
    date, `requested_*` the date it joined the pending list (creation by a
    seller, or the latest time it went back to pending)."""

    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    requested_from = django_filters.DateFilter(field_name="requested_at", lookup_expr="date__gte")
    requested_to = django_filters.DateFilter(field_name="requested_at", lookup_expr="date__lte")


class SellerListingFilter(_ListingDateFilters):
    """A seller's own product list."""

    class Meta:
        model = Listing
        fields = ["status", "listing_type", "category", "brand"]


class _GigPriceTypeFilter(django_filters.FilterSet):
    """`?price_type=weekly`: gigs that have an active package priced that way."""

    price_type = django_filters.ChoiceFilter(
        choices=ListingSku.PriceType.choices, method="filter_price_type"
    )

    def filter_price_type(self, queryset, name, value):
        return queryset.filter(skus__price_type=value, skus__is_active=True).distinct()


class SellerGigFilter(_GigPriceTypeFilter, _ListingDateFilters):
    """A seller's own gig list."""

    class Meta:
        model = Listing
        fields = ["status", "category"]


class SellerJobFilter(_GigPriceTypeFilter, _ListingDateFilters):
    """The seller's job board (`/seller/jobs/`) and "jobs I've bid on". `budget_min`/
    `budget_max` compare against the job's cheapest active budget SKU's
    `effective_price()` (discounted price only while its discount window is open,
    else the normal price)."""

    budget_min = django_filters.NumberFilter(method="filter_budget_min")
    budget_max = django_filters.NumberFilter(method="filter_budget_max")
    delivery_days_max = django_filters.NumberFilter(field_name="delivery_days", lookup_expr="lte")
    urgent = django_filters.BooleanFilter()

    class Meta:
        model = Listing
        fields = ["category", "country", "state", "city", "thana"]

    def _active_skus_with_effective_price(self, queryset):
        now = timezone.now()
        return queryset.filter(skus__is_active=True).annotate(
            _sku_effective_price=ListingSku.effective_price_expr(now, prefix="skus__")
        )

    def filter_budget_min(self, queryset, name, value):
        return self._active_skus_with_effective_price(queryset).filter(
            _sku_effective_price__gte=value
        ).distinct()

    def filter_budget_max(self, queryset, name, value):
        return self._active_skus_with_effective_price(queryset).filter(
            _sku_effective_price__lte=value
        ).distinct()
