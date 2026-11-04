from rest_framework.routers import SimpleRouter

from .views import PublicPaymentGatewayViewSet

router = SimpleRouter()
router.register("payment-gateways", PublicPaymentGatewayViewSet, basename="public-payment-gateway")

urlpatterns = router.urls
