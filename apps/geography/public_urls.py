from rest_framework.routers import SimpleRouter

from .public_views import PublicCityViewSet, PublicCountryViewSet, PublicStateViewSet, PublicThanaViewSet

# SimpleRouter, not DefaultRouter: no API-root page for the public routes.
router = SimpleRouter()
router.register("countries", PublicCountryViewSet, basename="public-country")
router.register("states", PublicStateViewSet, basename="public-state")
router.register("cities", PublicCityViewSet, basename="public-city")
router.register("thanas", PublicThanaViewSet, basename="public-thana")

urlpatterns = router.urls
