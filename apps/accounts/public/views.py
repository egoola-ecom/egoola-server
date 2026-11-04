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
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from ..models import Seller
from .serializers import PublicSellerSerializer


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
