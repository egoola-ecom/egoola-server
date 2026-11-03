from django.urls import path
from rest_framework.routers import DefaultRouter

from .buyer_address_views import BuyerAddressViewSet
from .buyer_order_views import BuyerOrderViewSet
from .buyer_views import CartItemDetailView, CartItemsView, CartSummaryView, CartView

router = DefaultRouter()
router.register("addresses", BuyerAddressViewSet, basename="buyer-address")
router.register("orders", BuyerOrderViewSet, basename="buyer-order")

urlpatterns = [
    path("cart/summary/", CartSummaryView.as_view(), name="buyer-cart-summary"),
    path("cart/", CartView.as_view(), name="buyer-cart"),
    path("cart/items/", CartItemsView.as_view(), name="buyer-cart-items"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="buyer-cart-item-detail"),
] + router.urls
