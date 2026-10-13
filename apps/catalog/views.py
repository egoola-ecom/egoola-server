from collections import defaultdict

from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminActor
from apps.core.models import ActorType
from apps.core.mixins import AuditedViewSetMixin
from apps.core.pagination import DefaultCursorPagination

from config.storage import delete_upload

from .filters import GigFilter, ListingFilter
from .models import Attribute, AttributeValue, Brand, Category, Listing, ListingStatusChangeLog, Measurement
from .serializers import (
    AttributeSerializer,
    AttributeValueSerializer,
    BrandSerializer,
    CategoryBriefSerializer,
    CategorySerializer,
    GigListSerializer,
    GigSerializer,
    ListingListSerializer,
    ListingSerializer,
    MeasurementSerializer,
)
from .thumbnail import ThumbnailViewSetMixin


class _InUseDeleteMixin:
    """409 instead of a crash when the row is still referenced by something
    protected (a listing, a listing SKU, ...) — deactivate it instead."""

    in_use_message = "This is still in use. Deactivate it instead of deleting."

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({"detail": self.in_use_message}, status=status.HTTP_409_CONFLICT)


class CategoryViewSet(
    _InUseDeleteMixin,
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
    in_use_message = (
        "This category, or one of its sub-categories, is used by one or more listings. "
        "Deactivate it instead of deleting."
    )

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


class AttributeViewSet(
    _InUseDeleteMixin,
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Product options such as Size or Colour — Create, Retrieve, Update, List
    (filter by name via `?name=` substring, or `?search=` which also matches
    the Bangla name; also `?is_active=`), Delete. Each attribute shows its
    values. One still used by a listing SKU can't be deleted — deactivate it."""

    permission_classes = [IsAdminActor]
    serializer_class = AttributeSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name", "name_bn"]
    in_use_message = "This attribute is used by one or more listing SKUs. Deactivate it instead of deleting."

    def get_queryset(self):
        queryset = Attribute.objects.prefetch_related("values")
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class AttributeValueViewSet(
    _InUseDeleteMixin,
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Values of an attribute (Size -> S, M, L, XL) — Create, Retrieve, Update,
    List (filter by `?attribute=` id, `?name=`, `?is_active=`; `?search=` also
    matches the Bangla name), Delete. One still used by a listing SKU can't be
    deleted — deactivate it."""

    permission_classes = [IsAdminActor]
    serializer_class = AttributeValueSerializer
    filterset_fields = ["attribute", "is_active"]
    search_fields = ["name", "name_bn"]
    in_use_message = "This value is used by one or more listing SKUs. Deactivate it instead of deleting."

    def get_queryset(self):
        queryset = AttributeValue.objects.select_related("attribute")
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class _AdminListingViewSet(ThumbnailViewSetMixin, AuditedViewSetMixin, viewsets.ModelViewSet):
    """Admin Listing Management & Moderation, shared by the product and the gig
    endpoints. Each subclass names the rows it may touch (`scope`) and its
    serializers; a row of another kind is a 404 there. Price tiers, media,
    SKUs and status-change history are handled through this same API (see
    ListingSerializer) — there's no separate media or price-tiers endpoint,
    same approach as Seller Management. The thumbnail has its own endpoint.

    Delete is soft: destroy() stamps deleted_at instead of removing the
    row, and Listing's default manager (ActiveListingManager) already
    excludes soft-deleted rows from every other query, so a deleted
    listing simply stops appearing anywhere without any extra filtering
    here."""

    permission_classes = [IsAdminActor]
    scope = Q()
    serializer_class = ListingSerializer
    list_serializer_class = ListingListSerializer
    # Used only by the pending list's OrderingFilter (below).
    ordering_fields = ["requested_at", "created_at", "title", "id"]
    ordering = ["-requested_at", "-id"]

    def get_serializer_class(self):
        if self.action in ("list", "listing_requests"):
            return self.list_serializer_class
        return self.serializer_class

    def get_queryset(self):
        rows = Listing.objects.filter(self.scope)
        if self.action == "list":
            return rows.select_related("category", "brand", "seller", "buyer").prefetch_related("skus")
        if self.action in ("update", "partial_update", "thumbnail"):
            # Lock the row for the whole save (see SellerListingViewSet).
            return rows.select_for_update(of=("self",))
        if self.action == "listing_requests":
            return rows.filter(status=Listing.Status.PENDING).select_related(
                "category", "brand", "seller", "buyer"
            ).prefetch_related("skus")
        return rows.select_related(
            "category", "brand", "seller", "buyer", "measurement", "country", "state", "city", "thana"
        ).prefetch_related(
            "price_tiers", "media", "status_change_logs", "info_change_logs",
            "skus__variants__attribute", "skus__variants__attribute_value",
        )

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["get"],
        url_path="requests",
        pagination_class=DefaultCursorPagination,
        filter_backends=[DjangoFilterBackend, SearchFilter, OrderingFilter],
    )
    def listing_requests(self, request):
        """GET .../requests/ — the admin's pending list: listings waiting
        for a decision (status `pending`), newest request first, cursor-paged
        (follow `next` / `previous`; no `count`). Same filters as the list."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        actor = request.user
        old_thumbnail = instance.image_path
        instance.deleted_at = timezone.now()
        instance.image_path = None  # the thumbnail file goes with the listing
        instance.image_url = None
        instance.updated_by = getattr(actor, "id", None)
        instance.updater_type = getattr(actor, "actor_type", ActorType.SYSTEM)
        instance.updater_name = getattr(actor, "name", None)
        with transaction.atomic():
            instance.save(update_fields=[
                "deleted_at", "image_path", "image_url", "updated_by", "updater_type", "updater_name", "updated_at",
            ])
            if old_thumbnail:
                transaction.on_commit(lambda: delete_upload(old_thumbnail))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk-moderate")
    def bulk_moderate(self, request):
        """POST .../bulk-moderate/
        {"listing_ids": [1, 2, 3], "status": "approved", "note": "..."}

        Applies one status to many listings in one call (an admin
        selecting several rows and approving/rejecting/requesting changes
        on all of them at once). Writes one ListingStatusChangeLog row per
        listing whose status actually changes; a listing already at the
        requested status is left alone (no-op, no log-row noise) and
        reported back as skipped rather than updated.
        """
        listing_ids = request.data.get("listing_ids") or []
        if not isinstance(listing_ids, list) or not all(
            isinstance(i, int) and not isinstance(i, bool) for i in listing_ids
        ):
            return Response({"listing_ids": "Must be a list of listing ids (integers)."}, status=400)
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
        actor_id = getattr(actor, "id", None)
        actor_type = getattr(actor, "actor_type", ActorType.SYSTEM)
        actor_name = getattr(actor, "name", None)
        updated_ids = []
        skipped_ids = []
        # All-or-nothing: a failure part-way must not leave some listings
        # moderated without their history row.
        with transaction.atomic():
            found = {listing.id: listing for listing in Listing.objects.filter(self.scope, id__in=listing_ids)}
            # Request order, each id once; unknown / deleted ids drop out.
            for listing in (found[i] for i in dict.fromkeys(listing_ids) if i in found):
                if listing.status == new_status:
                    skipped_ids.append(listing.id)
                    continue
                listing.status = new_status
                listing.note = note
                # Same audit stamp a single PATCH gets from AuditedViewSetMixin;
                # updated_at must be listed too, or save(update_fields) skips it.
                listing.updated_by = actor_id
                listing.updater_type = actor_type
                listing.updater_name = actor_name
                listing.save(
                    update_fields=[
                        "status", "note", "updated_by", "updater_type", "updater_name", "updated_at",
                    ]
                )
                ListingStatusChangeLog.objects.create(
                    listing=listing,
                    status=new_status,
                    note=note,
                    created_by=actor_id,
                    creator_type=actor_type,
                    creator_name=actor_name,
                )
                updated_ids.append(listing.id)

        return Response({"updated": updated_ids, "skipped": skipped_ids})


class ListingViewSet(_AdminListingViewSet):
    """Admin products (`/catalog/listings/`). Until the Job step is built it also
    manages a buyer's job requests (a service with `posted_by_role = buyer_request`).
    A seller's service offer is a gig and lives on `/catalog/gigs/`: it is not
    visible here (404)."""

    scope = Q(catalog_type=Listing.CatalogType.PRODUCT) | Q(posted_by_role=Listing.PostedByRole.BUYER_REQUEST)
    filterset_class = ListingFilter
    search_fields = ["title", "title_bn", "brand__name", "model", "skus__sku"]


class GigViewSet(_AdminListingViewSet):
    """Admin gigs (`/catalog/gigs/`): a seller's service offer. Create, update,
    list, details and delete, plus the pending list, bulk moderation and the
    thumbnail. Priced by SKUs, one per price type (hourly, daily, weekly,
    monthly, fixed)."""

    scope = Q(catalog_type=Listing.CatalogType.SERVICE, posted_by_role=Listing.PostedByRole.SELLER_OFFER)
    serializer_class = GigSerializer
    list_serializer_class = GigListSerializer
    filterset_class = GigFilter
    search_fields = ["title", "title_bn", "skus__sku"]
