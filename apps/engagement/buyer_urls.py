from django.urls import path

from .buyer_views import FavouriteDeleteView, FavouriteListCreateView

urlpatterns = [
    path("favourites/", FavouriteListCreateView.as_view(), name="buyer-favourites"),
    path("favourites/<int:listing_id>/", FavouriteDeleteView.as_view(), name="buyer-favourites-delete"),
]
