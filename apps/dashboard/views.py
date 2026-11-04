"""
Admin Dashboard summary (PRD: egoola-web/docs/prd/admin-dashboard-prd.md).

One aggregate-only endpoint replacing the 12 `?limit=1` list calls the admin
dashboard page used to make. Every figure marked "existing" in the PRD's
field table must equal the `count` of the matching list endpoint at the same
filter — see each query below for which existing list it mirrors.
"""

from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Admin, Seller, User
from apps.authentication.permissions import IsAdminActor
from apps.bidding.models import Bid
from apps.catalog.models import Listing
from apps.cms.models import Banner
from apps.orders.models import Cart, Order, Payment, PaymentStatusChangeHistory

# 30-60s per the PRD's non-functional section; `generated_at` in the payload
# tells the page how stale its copy is.
CACHE_KEY = "dashboard:summary:v1"
CACHE_TTL_SECONDS = 45

# Same scope `ListingViewSet`/`GigViewSet` (apps.catalog.admin_api.views) use,
# so `totals.listings`/`totals.gigs` and the pending/changes_requested counts
# below agree with `/catalog/listings/` and `/catalog/gigs/` exactly.
PRODUCT_SCOPE = Q(catalog_type=Listing.CatalogType.PRODUCT)
GIG_SCOPE = Q(catalog_type=Listing.CatalogType.SERVICE, posted_by_role=Listing.PostedByRole.SELLER_OFFER)

# PRD section 7.3's own key order.
ORDER_STATUS_KEYS = [
    Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.IN_PROGRESS, Order.Status.SHIPPED,
    Order.Status.DELIVERED, Order.Status.REJECTED, Order.Status.CANCELLED, Order.Status.COMPLETED,
    Order.Status.DISPUTED,
]


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _banners_live_count(now):
    """Same `active_now=true` definition as `BannerFilter` (apps.cms.filters)."""
    live = (
        Q(status=Banner.Status.ACTIVE)
        & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    )
    return Banner.objects.filter(live).count()


def _compute_summary():
    """Everything except `totals.admins` — that one is gated on the caller's
    own role, so it is never cached (see DashboardSummaryView.get)."""
    now = timezone.localtime()
    today = now.date()
    month_start = today.replace(day=1)

    by_status_counts = dict(Order.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    orders_by_status = {key.value: by_status_counts.get(key.value, 0) for key in ORDER_STATUS_KEYS}

    # "A payment that turned paid this month" -> the PaymentStatusChangeHistory
    # row recording that transition, not Order.payment_status (today's state,
    # not when it got there).
    paid_order_ids = PaymentStatusChangeHistory.objects.filter(
        current_status=Payment.Status.PAID,
        created_at__date__gte=month_start,
        created_at__date__lte=today,
    ).values_list("order_id", flat=True).distinct()
    paid_this_month = Order.objects.filter(id__in=paid_order_ids).aggregate(total=Sum("payable"))["total"]

    due_outstanding = (
        Order.objects.filter(payment_status=Payment.Status.DUE)
        .exclude(status__in=[Order.Status.CANCELLED, Order.Status.REJECTED])
        .aggregate(total=Sum("payable"))["total"]
    )

    return {
        "generated_at": now.isoformat(),
        "needs_attention": {
            "sellers_pending_review": Seller.objects.filter(
                verification_status=Seller.VerificationStatus.PENDING
            ).count(),
            "sellers_unverified": Seller.objects.filter(
                verification_status=Seller.VerificationStatus.UNVERIFIED
            ).count(),
            "listings_pending": Listing.objects.filter(PRODUCT_SCOPE, status=Listing.Status.PENDING).count(),
            "listings_changes_requested": Listing.objects.filter(
                PRODUCT_SCOPE, status=Listing.Status.CHANGES_REQUESTED
            ).count(),
            "gigs_pending": Listing.objects.filter(GIG_SCOPE, status=Listing.Status.PENDING).count(),
            "gigs_changes_requested": Listing.objects.filter(
                GIG_SCOPE, status=Listing.Status.CHANGES_REQUESTED
            ).count(),
            "orders_pending": Order.objects.filter(status=Order.Status.PENDING).count(),
            "orders_disputed": Order.objects.filter(status=Order.Status.DISPUTED).count(),
        },
        "totals": {
            "buyers": User.objects.count(),
            "sellers": Seller.objects.count(),
            "listings": Listing.objects.filter(PRODUCT_SCOPE).count(),
            "gigs": Listing.objects.filter(GIG_SCOPE).count(),
            "banners_live": _banners_live_count(now),
            "admins_all": Admin.objects.count(),
        },
        "orders": {
            "today": Order.objects.filter(created_at__date=today).count(),
            "this_month": Order.objects.filter(
                created_at__date__gte=month_start, created_at__date__lte=today
            ).count(),
            "by_status": orders_by_status,
            "revenue": {
                "currency": "BDT",
                "paid_this_month": _money(paid_this_month),
                "due_outstanding": _money(due_outstanding),
            },
        },
        "marketplace": {
            "open_carts": Cart.objects.filter(is_active=True).count(),
            "jobs_open_for_bidding": Listing.objects.filter(
                posted_by_role=Listing.PostedByRole.BUYER_REQUEST, status=Listing.Status.OPEN_FOR_BIDDING
            ).count(),
            "bids_pending": Bid.objects.filter(status=Bid.Status.PENDING).count(),
        },
    }


class DashboardSummaryView(APIView):
    """`GET /api/v1/dashboard/summary/` — every admin-dashboard tile in one
    call. Any admin may call it; `totals.admins` is `null` unless the caller
    is a super-admin (PRD section 7.2). No partial answers: a failure while
    computing fails the whole call (PRD section 7.5, rule 5)."""

    permission_classes = [IsAdminActor]

    def get(self, request):
        try:
            data = cache.get(CACHE_KEY)
            if data is None:
                data = _compute_summary()
                cache.set(CACHE_KEY, data, CACHE_TTL_SECONDS)
        except Exception:
            return Response({"detail": "Could not compute the dashboard summary."}, status=500)

        is_super_admin = request.user.type == Admin.AdminType.SUPER_ADMIN
        admins_all = data["totals"]["admins_all"]
        data = {**data, "totals": {**data["totals"], "admins": admins_all if is_super_admin else None}}
        del data["totals"]["admins_all"]
        return Response(data)
