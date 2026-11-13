import django_filters

from .models import Banner


class BannerFilter(django_filters.FilterSet):
    """`active_now=true` -> shown to visitors right now: status active and
    inside its schedule window (an empty start/end means no limit on that
    side). `active_now=false` -> everything else."""

    active_now = django_filters.BooleanFilter(method="filter_active_now")

    class Meta:
        model = Banner
        fields = ["placement", "status", "category"]

    def filter_active_now(self, queryset, name, value):
        live = Banner.live_q()
        return queryset.filter(live) if value else queryset.exclude(live)
