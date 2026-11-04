from rest_framework.routers import DefaultRouter

from .views import SellerOrderViewSet

router = DefaultRouter()
router.register("orders", SellerOrderViewSet, basename="seller-order")

urlpatterns = router.urls
