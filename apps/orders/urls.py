from rest_framework.routers import DefaultRouter

from .admin_order_views import AdminOrderViewSet
from .views import AdminCartViewSet, AdminPaymentGatewayViewSet

router = DefaultRouter()
router.register("carts", AdminCartViewSet, basename="admin-cart")
router.register("payment-gateways", AdminPaymentGatewayViewSet, basename="admin-payment-gateway")
router.register("orders", AdminOrderViewSet, basename="admin-order")

urlpatterns = router.urls
