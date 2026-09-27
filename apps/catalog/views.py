from collections import defaultdict

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminActor
from apps.core.mixins import AuditedViewSetMixin

from .models import Category, Measurement
from .serializers import CategoryBriefSerializer, CategorySerializer, MeasurementSerializer


class CategoryViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (filter by type/
    status, search by name), Delete. No retrieve, same as the Geography
    viewsets."""

    permission_classes = [IsAdminActor]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ["type", "status"]
    search_fields = ["name"]

    @action(detail=False, methods=["get"], url_path="parent-chain")
    def parent_chain(self, request):
        """GET /categories/parent-chain/?categoryIds=1,2

        For each requested category, returns its own details plus a
        `parents` array — ancestors ordered from the top-level ancestor
        (index 0) down to the immediate parent (last index). A category
        with no parent gets an empty `parents` array. Unknown/non-numeric
        ids are silently skipped.
        """
        raw_ids = request.query_params.get("categoryIds", "")
        ids = [int(part) for part in raw_ids.split(",") if part.strip().isdigit()]
        if not ids:
            return Response(
                {"categoryIds": "Provide one or more comma-separated category ids."}, status=400
            )

        # Whole table is small reference data — load it once so climbing
        # each requested category's ancestor chain needs no further queries.
        all_categories = {c.id: c for c in Category.objects.all()}

        results = []
        for cid in ids:
            category = all_categories.get(cid)
            if category is None:
                continue
            chain = []
            parent_id = category.parent_id
            while parent_id is not None:
                parent = all_categories.get(parent_id)
                if parent is None:
                    break
                chain.append(parent)
                parent_id = parent.parent_id
            chain.reverse()  # climbing collects immediate-parent-first; reverse to top-level-first

            data = CategoryBriefSerializer(category).data
            data["parents"] = CategoryBriefSerializer(chain, many=True).data
            results.append(data)

        return Response(results)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        """GET /categories/tree/?type=product&categoryName=elec

        Non-paginated full category hierarchy, for visualizing the tree
        while creating/attaching a category. `type` filters to one catalog
        type (product/service). `categoryName` is a case-insensitive
        substring match — matching nodes are kept along with their full
        ancestor path (for context) and their full descendant subtree (so
        the matched branch stays navigable); non-matching, unrelated
        branches are pruned out entirely.
        """
        category_type = request.query_params.get("type")
        category_name = request.query_params.get("categoryName", "").strip()

        queryset = Category.objects.all()
        if category_type:
            queryset = queryset.filter(type=category_type)
        categories = {c.id: c for c in queryset}

        if category_name:
            needle = category_name.lower()
            matched_ids = {cid for cid, c in categories.items() if needle in c.name.lower()}
            keep_ids = set(matched_ids)

            for cid in matched_ids:
                parent_id = categories[cid].parent_id
                while parent_id is not None and parent_id in categories and parent_id not in keep_ids:
                    keep_ids.add(parent_id)
                    parent_id = categories[parent_id].parent_id

            children_by_parent = defaultdict(list)
            for c in categories.values():
                children_by_parent[c.parent_id].append(c)

            def add_descendants(cid):
                for child in children_by_parent.get(cid, []):
                    if child.id not in keep_ids:
                        keep_ids.add(child.id)
                        add_descendants(child.id)

            for cid in list(matched_ids):
                add_descendants(cid)

            categories = {cid: c for cid, c in categories.items() if cid in keep_ids}

        children_by_parent = defaultdict(list)
        for c in categories.values():
            children_by_parent[c.parent_id].append(c)

        def serialize(category):
            return {
                "id": category.id,
                "type": category.type,
                "name": category.name,
                "slug": category.slug,
                "image_path": category.image_path,
                "image_url": category.image_url,
                "sort_order": category.sort_order,
                "status": category.status,
                "children": [serialize(child) for child in children_by_parent.get(category.id, [])],
            }

        tree_data = [serialize(root) for root in children_by_parent.get(None, [])]
        return Response(tree_data)


class MeasurementViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed reference data — Create, Update, List (search by name),
    Delete. No retrieve, same as Category/Geography."""

    permission_classes = [IsAdminActor]
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer
    search_fields = ["name"]
