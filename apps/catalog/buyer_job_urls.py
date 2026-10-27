from rest_framework.routers import DefaultRouter

from .buyer_job_views import BuyerJobViewSet

router = DefaultRouter()
router.register("jobs", BuyerJobViewSet, basename="buyer-job")

urlpatterns = router.urls
