"""
Public seller profile — what a buyer sees when they tap a seller's name on a
product or a gig. No login (`authentication_classes = []`, like the other public
routes, see docs/public-api-guide.md).

Only a seller who can operate (verified **and** active) has a public page: any
other seller (waiting, rejected, paused, suspended) is a `404`, exactly like
their listings, which are hidden too. Nothing private is returned: no email,
phone, address, documents, balance or verification notes.
"""

from django.db.models import Q
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from .models import Seller


def public_sellers():
    """Sellers a buyer may see: verified and active."""
    return Seller.objects.filter(
        verification_status=Seller.VerificationStatus.VERIFIED, status=Seller.Status.ACTIVE
    )


def public_seller_listings_q(prefix="seller"):
    """Q for a listing: no owner (an admin's own listing), or a seller a buyer may see."""
    return Q(**{f"{prefix}__isnull": True}) | Q(
        **{
            f"{prefix}__verification_status": Seller.VerificationStatus.VERIFIED,
            f"{prefix}__status": Seller.Status.ACTIVE,
        }
    )


class PublicSellerBriefSerializer(serializers.ModelSerializer):
    """The seller block on a listing: enough to show the name and link to the profile."""

    class Meta:
        model = Seller
        fields = ["id", "name", "profile_pic_url"]


class PublicSellerSerializer(serializers.ModelSerializer):
    """The seller's public page."""

    member_since = serializers.DateTimeField(source="created_at", read_only=True)
    location = serializers.SerializerMethodField()
    business = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True)
    gig_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Seller
        fields = [
            "id", "name", "profile_pic_url", "member_since", "location", "business", "contact",
            "skills", "education", "experience", "product_count", "gig_count",
        ]

    def get_location(self, obj):
        info = getattr(obj, "info", None)
        place = info if info is not None and (info.country_id or info.city_id) else obj
        return {
            "country": place.country.name if place.country_id else None,
            "state": place.state.name if place.state_id else None,
            "city": place.city.name if place.city_id else None,
            "thana": place.thana.name if place.thana_id else None,
        }

    def get_business(self, obj):
        info = getattr(obj, "info", None)
        if info is None:
            return None
        return {
            "business_type": info.business_type,
            "main_product": info.main_product,
            "description": info.description,
            "established_year": info.established_year,
            "employees_range": info.employees_range,
        }

    def get_contact(self, obj):
        info = getattr(obj, "info", None)
        if info is None:
            return None
        return {
            "public_email": info.public_email, "whatsapp": info.whatsapp, "facebook": info.facebook,
            "wechat": info.wechat, "skype": info.skype,
        }


class PublicSellerDetailView(RetrieveAPIView):
    """`GET /api/v1/public/sellers/{id}/` — see PublicSellerSerializer."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicSellerSerializer

    def get_queryset(self):
        from django.db.models import Count

        from apps.catalog.models import Listing

        live = Q(
            listings__status=Listing.Status.APPROVED, listings__deleted_at__isnull=True,
            listings__skus__is_active=True,  # something to buy: the same rule as the public lists
        )
        return (
            public_sellers()
            .select_related("info", "country", "state", "city", "thana",
                            "info__country", "info__state", "info__city", "info__thana")
            .annotate(
                product_count=Count(
                    "listings", distinct=True,
                    filter=live & Q(listings__catalog_type=Listing.CatalogType.PRODUCT),
                ),
                gig_count=Count(
                    "listings", distinct=True,
                    filter=live & Q(
                        listings__catalog_type=Listing.CatalogType.SERVICE,
                        listings__posted_by_role=Listing.PostedByRole.SELLER_OFFER,
                    ),
                ),
            )
        )
