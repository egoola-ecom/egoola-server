from collections import defaultdict

from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminActor
from apps.core.models import ActorType
from apps.core.mixins import AuditedViewSetMixin

from .models import Brand, Category, Listing, ListingStatusChangeLog, Measurement
from .serializers import (
    BrandSerializer,
    CategoryBriefSerializer,
    CategorySerializer,
    ListingListSerializer,
    ListingSerializer,
    MeasurementSerializer,
)


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


class BrandViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-managed Brand list under the Listing module — Create, Update,
    List (filter by name via `?name=` substring, or `?search=`; also
    `?is_active=`), Delete. A brand still used by a listing can't be
    deleted — deactivate it (is_active=false) instead."""

    permission_classes = [IsAdminActor]
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This brand is used by one or more listings. Deactivate it instead of deleting."},
                status=status.HTTP_409_CONFLICT,
            )


class ListingViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Admin Listing Management & Moderation. Price tiers, media, and
    status-change history are handled through this same API (see
    ListingSerializer) — there's no separate /listings/{id}/media/ or
    /listings/{id}/price-tiers/ endpoint, same approach as Seller
    Management.

    Delete is soft: destroy() stamps deleted_at instead of removing the
    row, and Listing's default manager (ActiveListingManager) already
    excludes soft-deleted rows from every other query, so a deleted
    listing simply stops appearing anywhere without any extra filtering
    here."""

    permission_classes = [IsAdminActor]
    filterset_fields = ["status", "catalog_type", "listing_type", "category", "brand", "seller", "buyer"]
    search_fields = ["title", "brand__name", "model"]

    def get_serializer_class(self):
        return ListingListSerializer if self.action == "list" else ListingSerializer

    def get_queryset(self):
        if self.action == "list":
            return Listing.objects.select_related("category", "brand", "seller", "buyer")
        return Listing.objects.select_related(
            "category", "brand", "seller", "buyer", "measurement", "country", "state", "city", "thana"
        ).prefetch_related("price_tiers", "media", "status_change_logs")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk-moderate")
    def bulk_moderate(self, request):
        """POST /listings/bulk-moderate/
        {"listing_ids": [1, 2, 3], "status": "approved", "note": "..."}

        Applies one status to many listings in one call (an admin
        selecting several rows and approving/rejecting/requesting changes
        on all of them at once). Writes one ListingStatusChangeLog row per
        listing whose status actually changes; a listing already at the
        requested status is left alone (no-op, no log-row noise) and
        reported back as skipped rather than updated.
        """
        listing_ids = request.data.get("listing_ids") or []
        new_status = request.data.get("status")
        note = request.data.get("note") or None

        valid_statuses = {Listing.Status.APPROVED, Listing.Status.REJECTED, Listing.Status.CHANGES_REQUESTED}
        if new_status not in valid_statuses:
            return Response(
                {"status": f"Must be one of: {', '.join(sorted(valid_statuses))}."}, status=400
            )
        if new_status in (Listing.Status.REJECTED, Listing.Status.CHANGES_REQUESTED) and not note:
            return Response(
                {"note": "A note is required when rejecting or requesting changes."},
                status=400,
            )
        if not listing_ids:
            return Response({"listing_ids": "Provide one or more listing ids."}, status=400)

        actor = request.user
        updated_ids = []
        skipped_ids = []
        for listing in Listing.objects.filter(id__in=listing_ids):
            if listing.status == new_status:
                skipped_ids.append(listing.id)
                continue
            listing.status = new_status
            listing.note = note
            listing.save(update_fields=["status", "note"])
            ListingStatusChangeLog.objects.create(
                listing=listing,
                status=new_status,
                note=note,
                created_by=getattr(actor, "id", None),
                creator_type=getattr(actor, "actor_type", ActorType.SYSTEM),
                creator_name=getattr(actor, "name", None),
            )
            updated_ids.append(listing.id)

        return Response({"updated": updated_ids, "skipped": skipped_ids})
