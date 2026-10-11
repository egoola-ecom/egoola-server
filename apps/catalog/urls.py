from rest_framework.routers import DefaultRouter

from .views import (
    AttributeValueViewSet,
    AttributeViewSet,
    BrandViewSet,
    CategoryViewSet,
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

urlpatterns = router.urls
