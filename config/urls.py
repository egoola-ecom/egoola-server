"""
Root URLconf.

Every API endpoint is versioned and grouped by app, per the Planning
document Section 4.3: /api/v1/<app>/... . Each app owns its own urls.py;
this file only wires the version prefix and the cross-cutting endpoints
(auth, schema/docs, admin).
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

API_V1 = [
    path("geography/", include("apps.geography.urls")),
    # Read-only lists that need no login (sign-up form dropdowns) — see
    # apps/geography/public_views.py.
    path("public/geography/", include("apps.geography.public_urls")),
    # Read-only catalog lists for browsing (the Buyer Panel): no login.
    path("public/catalog/", include("apps.catalog.public_urls")),
    path("public/sellers/", include("apps.accounts.public_urls")),
    path("accounts/", include("apps.accounts.urls")),
    # The logged-in seller's own endpoints (profile, resubmit, password).
    path("seller/", include("apps.accounts.seller_urls")),
    # The seller's own listings and the lookups for the listing form.
    path("seller/", include("apps.catalog.seller_urls")),
    # Login (one endpoint per actor table) + token refresh — see
    # apps.authentication. Kept as its own app/urls.py rather than
    # apps.accounts, since "prove who you are" and "manage Admin/Seller/
    # Buyer records" are different concerns.
    path("auth/", include("apps.authentication.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("bidding/", include("apps.bidding.urls")),
    path("orders/", include("apps.orders.urls")),
    # The logged-in buyer's own cart and wishlist.
    path("buyer/", include("apps.orders.buyer_urls")),
    path("buyer/", include("apps.engagement.buyer_urls")),
    path("inquiries/", include("apps.inquiries.urls")),
    path("messaging/", include("apps.messaging.urls")),
    path("engagement/", include("apps.engagement.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("cms/", include("apps.cms.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(API_V1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Serves files saved to MEDIA_ROOT (the local "bucket" stand-in, used only
# when DJANGO_ENV=local — see config/storage.py) over HTTP in development
# only — `static()` is a no-op unless DEBUG is on. Once DJANGO_ENV switches
# to a real environment, files are served directly from S3's own URLs
# instead, never through Django.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
