from rest_framework.routers import DefaultRouter

from .views import AdminFavouriteViewSet

router = DefaultRouter()
router.register("favourites", AdminFavouriteViewSet, basename="admin-favourite")

urlpatterns = router.urls
