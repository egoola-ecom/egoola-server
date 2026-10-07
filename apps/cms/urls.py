from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BannerViewSet, EmailTemplateViewSet, SettingViewSet, SiteLogoView

router = DefaultRouter()
router.register("banners", BannerViewSet, basename="banner")
router.register("email-templates", EmailTemplateViewSet, basename="email-template")
router.register("settings", SettingViewSet, basename="setting")

urlpatterns = [
    path("site-logo/", SiteLogoView.as_view(), name="site-logo"),
    *router.urls,
]
