from django.urls import path

from .buyer_views import CartItemDetailView, CartItemsView, CartView

urlpatterns = [
    path("cart/", CartView.as_view(), name="buyer-cart"),
    path("cart/items/", CartItemsView.as_view(), name="buyer-cart-items"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="buyer-cart-item-detail"),
]
