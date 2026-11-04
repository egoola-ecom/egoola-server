import django_filters

from ..models import Bid


class SellerBidFilter(django_filters.FilterSet):
    class Meta:
        model = Bid
        fields = ["status", "listing"]
