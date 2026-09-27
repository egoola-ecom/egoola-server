from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, MeasurementViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("measurements", MeasurementViewSet, basename="measurement")

urlpatterns = router.urls
