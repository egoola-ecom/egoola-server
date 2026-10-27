from rest_framework.routers import DefaultRouter

from .views import AdminCartViewSet

router = DefaultRouter()
router.register("carts", AdminCartViewSet, basename="admin-cart")

urlpatterns = router.urls
