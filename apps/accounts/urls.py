from rest_framework.routers import DefaultRouter

from .views import AdminViewSet, BuyerViewSet, SellerViewSet

router = DefaultRouter()
router.register("admins", AdminViewSet, basename="admin")
router.register("sellers", SellerViewSet, basename="seller")
router.register("buyers", BuyerViewSet, basename="buyer")

urlpatterns = router.urls
