import django_filters

from .models import Listing


class _ListingDateFilters(django_filters.FilterSet):
    """Shared date filters (inclusive, YYYY-MM-DD): `created_*` is the creation
    date, `requested_*` the date it joined the pending list (creation by a
    seller, or the latest time it went back to pending)."""

    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    requested_from = django_filters.DateFilter(field_name="requested_at", lookup_expr="date__gte")
    requested_to = django_filters.DateFilter(field_name="requested_at", lookup_expr="date__lte")


class ListingFilter(_ListingDateFilters):
    """Admin listing list and pending list."""

    class Meta:
        model = Listing
        fields = ["status", "catalog_type", "listing_type", "category", "brand", "seller", "buyer"]


class SellerListingFilter(_ListingDateFilters):
    """A seller's own listing list."""

    class Meta:
        model = Listing
        fields = ["status", "catalog_type", "listing_type", "category", "brand"]
