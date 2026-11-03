from rest_framework.routers import DefaultRouter

from .admin_views import AdminBidViewSet

router = DefaultRouter()
router.register("bids", AdminBidViewSet, basename="admin-bid")

urlpatterns = router.urls
