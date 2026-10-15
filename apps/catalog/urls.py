from django.urls import path
from rest_framework.routers import DefaultRouter

from .listing_files import AdminListingFilesView

from .views import (
    AttributeValueViewSet,
    AttributeViewSet,
    BrandViewSet,
    CategoryViewSet,
    GigViewSet,
    ListingViewSet,
    MeasurementViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("measurements", MeasurementViewSet, basename="measurement")
router.register("brands", BrandViewSet, basename="brand")
router.register("attributes", AttributeViewSet, basename="attribute")
router.register("attribute-values", AttributeValueViewSet, basename="attribute-value")
router.register("listings", ListingViewSet, basename="listing")
router.register("gigs", GigViewSet, basename="gig")

urlpatterns = [
    path("listing-files/<int:listing_id>/", AdminListingFilesView.as_view(), name="listing-files"),
    *router.urls,
]
