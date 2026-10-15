"""
Public, read-only catalog lists for the Buyer Panel (browsing needs no login).

Like the public geography lists these are separate from the admin endpoints:
they carry no audit columns and accept only GET. `authentication_classes = []`
so a stale or expired token never turns a public read into a 401.
"""

from django.db.models import Exists, OuterRef, Q
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from apps.core.pagination import BuyerPagePagination

from .models import Category


class PublicCategorySerializer(serializers.ModelSerializer):
    """One category for browsing. `has_children` says whether there is anything
    to drill into (an active sub-category), so the app can show an arrow."""

    has_children = serializers.BooleanField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "parent", "type", "name", "name_bn", "slug", "image_url", "sort_order", "has_children"]


class CategoryListQuerySerializer(serializers.Serializer):
    """The query string of the category list: validated, with its defaults."""

    parent_id = serializers.IntegerField(required=False, min_value=1)
    search = serializers.CharField(required=False, allow_blank=True, max_length=100, trim_whitespace=True)
    type = serializers.ChoiceField(required=False, choices=Category.CatalogType.choices)
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=BuyerPagePagination.max_page_size)


def _hidden_category_ids():
    """Ids of categories that are inactive or sit under an inactive ancestor.

    A sub-category of an inactive category must not show up either (it cannot be
    reached by browsing, and a search must not leak it). The category table is a
    small reference table, so one light query is cheaper than a recursive one."""
    rows = list(Category.objects.values_list("id", "parent_id", "status"))
    parent_of = {id_: parent for id_, parent, _ in rows}
    inactive = {id_ for id_, _, status in rows if status != Category.Status.ACTIVE}
    hidden = set()
    for id_ in parent_of:
        node, seen = id_, set()
        while node is not None and node not in seen:
            if node in inactive:
                hidden.add(id_)
                break
            seen.add(node)
            node = parent_of.get(node)
    return hidden


class PublicCategoryListView(ListAPIView):
    """`GET /api/v1/public/catalog/categories/` — the one category list of the Buyer Panel.

    | Query | Meaning |
    |---|---|
    | *(none)* | the **top-level** categories (no parent) |
    | `parent_id=7` | the **direct children** of category 7 (`404` if it does not exist or is inactive) |
    | `search=phone` | partial, case-insensitive match on `name` or `name_bn`. **With** `parent_id`: among that parent's direct children. **Without**: across every level |
    | `type=product\\|service` | only that kind of category |
    | `page`, `page_size` | page-based paging (`page_size` default 20, max 100) |

    Inactive categories, and everything under an inactive category, are never
    returned. Order: `sort_order`, then `name`."""

    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = BuyerPagePagination
    serializer_class = PublicCategorySerializer

    def get_queryset(self):
        query = CategoryListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data

        rows = Category.objects.filter(status=Category.Status.ACTIVE)
        parent_id = params.get("parent_id")
        search = params.get("search")
        hidden = _hidden_category_ids() if (parent_id or search) else set()

        if parent_id is not None:
            if parent_id in hidden or not Category.objects.filter(pk=parent_id).exists():
                raise NotFound("Category not found.")
            rows = rows.filter(parent_id=parent_id)
        elif not search:
            rows = rows.filter(parent__isnull=True)  # the default: the top level
        if search:
            rows = rows.filter(Q(name__icontains=search) | Q(name_bn__icontains=search))
            if hidden:
                rows = rows.exclude(id__in=hidden)
        if params.get("type"):
            rows = rows.filter(type=params["type"])

        has_children = Category.objects.filter(parent=OuterRef("pk"), status=Category.Status.ACTIVE)
        return rows.annotate(has_children=Exists(has_children)).order_by("sort_order", "name", "id")
