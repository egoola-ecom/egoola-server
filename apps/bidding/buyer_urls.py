from django.urls import path

from .buyer_views import BuyerJobBidListView

urlpatterns = [
    path("jobs/<int:job_id>/bids/", BuyerJobBidListView.as_view(), name="buyer-job-bids"),
]
