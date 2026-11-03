from django.urls import path

from .buyer_views import BuyerBidAcceptView, BuyerJobBidListView

urlpatterns = [
    path("jobs/<int:job_id>/bids/", BuyerJobBidListView.as_view(), name="buyer-job-bids"),
    path("jobs/<int:job_id>/bids/<int:bid_id>/accept/", BuyerBidAcceptView.as_view(), name="buyer-job-bid-accept"),
]
