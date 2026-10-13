from rest_framework.routers import SimpleRouter

from .seller_views import (
    SellerAttributeLookupViewSet,
    SellerBrandLookupViewSet,
    SellerCategoryLookupViewSet,
    SellerGigViewSet,
    SellerListingViewSet,
    SellerMeasurementLookupViewSet,
)

# SimpleRouter: no API-root page. Mounted at /api/v1/seller/ (see config/urls.py).
router = SimpleRouter()
router.register("listings", SellerListingViewSet, basename="seller-listing")
router.register("gigs", SellerGigViewSet, basename="seller-gig")
router.register("lookups/categories", SellerCategoryLookupViewSet, basename="seller-lookup-category")
router.register("lookups/brands", SellerBrandLookupViewSet, basename="seller-lookup-brand")
router.register("lookups/measurements", SellerMeasurementLookupViewSet, basename="seller-lookup-measurement")
router.register("lookups/attributes", SellerAttributeLookupViewSet, basename="seller-lookup-attribute")

urlpatterns = router.urls
