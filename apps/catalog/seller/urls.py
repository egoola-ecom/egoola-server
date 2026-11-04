from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from ..listing_files import SellerListingFilesView
from .views import (
    SellerAttributeLookupViewSet,
    SellerBrandLookupViewSet,
    SellerCategoryLookupViewSet,
    SellerGigViewSet,
    SellerJobViewSet,
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

# DefaultRouter, same as the old seller_job_urls.py — keeps its API-root view.
job_router = DefaultRouter()
job_router.register("jobs", SellerJobViewSet, basename="seller-job")

urlpatterns = [
    path("listing-files/<int:listing_id>/", SellerListingFilesView.as_view(), name="seller-listing-files"),
    *router.urls,
    *job_router.urls,
]
