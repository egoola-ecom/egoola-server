from rest_framework.routers import DefaultRouter

from .seller_job_views import SellerJobViewSet

router = DefaultRouter()
router.register("jobs", SellerJobViewSet, basename="seller-job")

urlpatterns = router.urls
