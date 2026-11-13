from rest_framework.routers import SimpleRouter

from .views import PublicBannerViewSet

router = SimpleRouter()
router.register("banners", PublicBannerViewSet, basename="public-banner")

urlpatterns = router.urls
