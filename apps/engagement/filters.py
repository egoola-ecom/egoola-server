import django_filters
from django.db.models import Exists, OuterRef

from apps.catalog.models import Listing
from apps.catalog.public_listings import buyer_visible_listings

from .models import Favourite


class FavouriteFilter(django_filters.FilterSet):
    """Admin wishlist list filters.

    - `buyer`: exact buyer id.
    - `listing`: exact listing id.
    - `catalog_type`: product / service (of the saved listing).
    - `listing_visible`: true/false — whether the saved listing currently
      passes the buyer-facing visibility rule (approved, seller verified and
      active). Admin sees every favourite either way; this only narrows it.
    - `created_from` / `created_to`: inclusive dates (YYYY-MM-DD).
    """

    catalog_type = django_filters.ChoiceFilter(field_name="listing__catalog_type", choices=Listing.CatalogType.choices)
    listing_visible = django_filters.BooleanFilter(method="filter_listing_visible")
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Favourite
        fields = ["buyer", "listing"]

    def filter_listing_visible(self, queryset, name, value):
        visible = Exists(buyer_visible_listings().filter(pk=OuterRef("listing_id")))
        return queryset.filter(visible) if value else queryset.exclude(visible)
