from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AdminLoginView, BuyerLoginView, SellerLoginView

urlpatterns = [
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("seller/login/", SellerLoginView.as_view(), name="seller-login"),
    path("buyer/login/", BuyerLoginView.as_view(), name="buyer-login"),
    # SimpleJWT copies every custom claim (actor_type, actor_id) from the
    # refresh token onto the new access token automatically, so one shared
    # refresh view covers all three actors — no per-actor version needed.
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
