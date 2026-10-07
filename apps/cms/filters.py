import django_filters
from django.db.models import Q
from django.utils import timezone

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
        now = timezone.now()
        live = (
            Q(status=Banner.Status.ACTIVE)
            & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        )
        return queryset.filter(live) if value else queryset.exclude(live)
