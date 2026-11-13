"""
Public, read-only banner list — for the buyer homepage/hero, which must not
depend on an admin token to find out which banners to show.

Deliberately a separate set of endpoints from the admin banner API
(`/api/v1/cms/banners/`), not a loosened version of it: that one carries
audit columns, accepts writes, and lists every banner regardless of status
or schedule. This returns only banners that are currently live: `status`
is `active` and the current time falls inside `starts_at`/`ends_at` (either
side left blank means open-ended on that side).

`authentication_classes = []` so a stale or expired token in the browser
can never turn a public read into a 401. Optional `?placement=` filters to
one of hero/sidebar/category.
"""

from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from ..models import Banner
from .serializers import PublicBannerSerializer


class PublicBannerViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicBannerSerializer
    pagination_class = None
    filterset_fields = ["placement"]

    def get_queryset(self):
        return Banner.objects.filter(Banner.live_q())
