import django_filters

from .models import Listing, ListingSku


class _ListingDateFilters(django_filters.FilterSet):
    """Shared date filters (inclusive, YYYY-MM-DD): `created_*` is the creation
    date, `requested_*` the date it joined the pending list (creation by a
    seller, or the latest time it went back to pending)."""

    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    requested_from = django_filters.DateFilter(field_name="requested_at", lookup_expr="date__gte")
    requested_to = django_filters.DateFilter(field_name="requested_at", lookup_expr="date__lte")


class ListingFilter(_ListingDateFilters):
    """Admin listing list and pending list (products, and for now job requests)."""

    class Meta:
        model = Listing
        fields = ["status", "catalog_type", "listing_type", "category", "brand", "seller", "buyer"]


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


class GigFilter(_GigPriceTypeFilter, _ListingDateFilters):
    """Admin gig list and pending gig list."""

    class Meta:
        model = Listing
        fields = ["status", "category", "seller"]


class SellerGigFilter(_GigPriceTypeFilter, _ListingDateFilters):
    """A seller's own gig list."""

    class Meta:
        model = Listing
        fields = ["status", "category"]
