from django.urls import path

from .public_listings import PublicGigDetailView, PublicGigListView, PublicProductDetailView, PublicProductListView
from .public_views import PublicCategoryListView

urlpatterns = [
    path("categories/", PublicCategoryListView.as_view(), name="public-category-list"),
    path("products/", PublicProductListView.as_view(), name="public-product-list"),
    path("products/<int:pk>/", PublicProductDetailView.as_view(), name="public-product-detail"),
    path("gigs/", PublicGigListView.as_view(), name="public-gig-list"),
    path("gigs/<int:pk>/", PublicGigDetailView.as_view(), name="public-gig-detail"),
]
