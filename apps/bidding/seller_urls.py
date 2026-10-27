from django.urls import path
from rest_framework.routers import DefaultRouter

from .seller_views import SellerBidViewSet, SellerJobBidCreateView

router = DefaultRouter()
router.register("bids", SellerBidViewSet, basename="seller-bid")

urlpatterns = [
    path("jobs/<int:job_id>/bids/", SellerJobBidCreateView.as_view(), name="seller-job-bid-create"),
] + router.urls
