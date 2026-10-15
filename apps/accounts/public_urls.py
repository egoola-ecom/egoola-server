from django.urls import path

from .public_views import PublicSellerDetailView

urlpatterns = [
    path("<int:pk>/", PublicSellerDetailView.as_view(), name="public-seller-detail"),
]
