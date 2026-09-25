"""
Root URLconf.

Every API endpoint is versioned and grouped by app, per the Planning
document Section 4.3: /api/v1/<app>/... . Each app owns its own urls.py;
this file only wires the version prefix and the cross-cutting endpoints
(auth, schema/docs, admin).
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

API_V1 = [
    path("geography/", include("apps.geography.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("bidding/", include("apps.bidding.urls")),
    path("orders/", include("apps.orders.urls")),
    path("inquiries/", include("apps.inquiries.urls")),
    path("messaging/", include("apps.messaging.urls")),
    path("engagement/", include("apps.engagement.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("cms/", include("apps.cms.urls")),
    # Phase 0 Backend, task 7: basic JWT login wiring against Django's
    # built-in auth.User. The three actor-specific login flows (Admin,
    # Seller, Buyer, with OTP for the latter two) are Phase 1 scope.
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(API_V1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
