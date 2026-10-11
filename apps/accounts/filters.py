import django_filters

from apps.core.models import ActorType

from .models import Seller, User


class SellerFilter(django_filters.FilterSet):
    """Seller list filters — used by both the normal list and the Seller
    Request queue.

    - `verification_status`, `status`: exact, or several at once with
      `verification_status__in=unverified,pending`.
    - `is_seller_request`: true/false flag (in the admin's request queue or not).
    - `creator_type`: who created the account — `seller` = registered by
      themselves, `admin` = created by an admin.
    - `email_verified` / `phone_verified` / `has_business_profile`: true/false.
    - `business_type`: text search inside the business profile's type.
    - `country` / `state` / `city` / `thana`: geography ids.
    - `created_from` / `created_to`: inclusive dates (YYYY-MM-DD) on signup date.
    """

    is_seller_request = django_filters.BooleanFilter()
    creator_type = django_filters.ChoiceFilter(choices=ActorType.choices)
    email_verified = django_filters.BooleanFilter(field_name="email_verified_at", lookup_expr="isnull", exclude=True)
    phone_verified = django_filters.BooleanFilter(field_name="phone_verified_at", lookup_expr="isnull", exclude=True)
    has_business_profile = django_filters.BooleanFilter(field_name="info", lookup_expr="isnull", exclude=True)
    business_type = django_filters.CharFilter(field_name="info__business_type", lookup_expr="icontains")
    created_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Seller
        fields = {
            "verification_status": ["exact", "in"],
            "status": ["exact", "in"],
            "country": ["exact"],
            "state": ["exact"],
            "city": ["exact"],
            "thana": ["exact"],
        }


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
