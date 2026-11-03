from rest_framework.routers import SimpleRouter

from .public_views import PublicPaymentGatewayViewSet

# SimpleRouter, not DefaultRouter: no API-root page for the public routes.
router = SimpleRouter()
router.register("payment-gateways", PublicPaymentGatewayViewSet, basename="public-payment-gateway")

urlpatterns = router.urls
