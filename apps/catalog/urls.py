from rest_framework.routers import DefaultRouter

from .views import BrandViewSet, CategoryViewSet, ListingViewSet, MeasurementViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("measurements", MeasurementViewSet, basename="measurement")
router.register("brands", BrandViewSet, basename="brand")
router.register("listings", ListingViewSet, basename="listing")

urlpatterns = router.urls
