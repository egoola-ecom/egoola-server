from rest_framework.routers import DefaultRouter

from .views import CityViewSet, CountryViewSet, StateViewSet, ThanaViewSet

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("states", StateViewSet, basename="state")
router.register("cities", CityViewSet, basename="city")
router.register("thanas", ThanaViewSet, basename="thana")

urlpatterns = router.urls
