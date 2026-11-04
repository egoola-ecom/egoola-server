from rest_framework.routers import DefaultRouter

from .views import AdminBidViewSet

router = DefaultRouter()
router.register("bids", AdminBidViewSet, basename="admin-bid")

urlpatterns = router.urls
