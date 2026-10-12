from django.urls import path

from .seller_views import SellerChangePasswordView, SellerMeView, SellerResubmitView

urlpatterns = [
    path("me/", SellerMeView.as_view(), name="seller-me"),
    path("me/resubmit/", SellerResubmitView.as_view(), name="seller-me-resubmit"),
    path("me/change-password/", SellerChangePasswordView.as_view(), name="seller-me-change-password"),
]
