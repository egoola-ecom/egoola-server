"""
Public product and gig APIs for the Buyer Panel (no login, GET only):

    GET /public/catalog/products/       GET /public/catalog/products/{id}/
    GET /public/catalog/gigs/           GET /public/catalog/gigs/{id}/

What a buyer may see: only `approved`, not deleted listings, of a seller who is
verified and active (or of no seller, an admin's own listing), and with at least
one active SKU. A product id on the gigs API is a 404 and the reverse. Nothing
internal is returned (no status notes, logs, audit columns or seller contact
details). Prices are those of the **active** SKUs only. Paging is the Buyer
Panel's page-based paging. See docs/public-api-guide.md.
"""

from django.db.models import Case, DecimalField, Exists, F, OuterRef, Prefetch, Q, Subquery, When
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from apps.accounts.public_views import PublicSellerBriefSerializer, public_seller_listings_q
from apps.core.pagination import BuyerPagePagination

from .models import Category, Listing, ListingMedia, ListingPriceTier, ListingSku, ListingSkuVariant

PRODUCT_SCOPE = Q(catalog_type=Listing.CatalogType.PRODUCT) & ~Q(posted_by_role=Listing.PostedByRole.BUYER_REQUEST)
GIG_SCOPE = Q(catalog_type=Listing.CatalogType.SERVICE, posted_by_role=Listing.PostedByRole.SELLER_OFFER)

ORDERINGS = {
    "newest": ("-created_at", "-id"),
    "oldest": ("created_at", "id"),
    "price_asc": ("min_price", "-created_at", "-id"),
    "price_desc": ("-min_price", "-created_at", "-id"),
    "title": ("title", "id"),
}


def buyer_visible_listings():
    """Listings a buyer may act on — add to cart, favourite — not just browse:
    the same visibility rule as the public lists above (approved, seller
    verified and active, never a buyer's own job request). Shared so every
    buyer-facing feature enforces this one rule the same way."""
    return Listing.objects.filter(
        PRODUCT_SCOPE | GIG_SCOPE, public_seller_listings_q(), status=Listing.Status.APPROVED
    )


# --------------------------------------------------------------------- query string


class _ListQuerySerializer(serializers.Serializer):
    """The query string shared by both lists, validated (a bad value is a 400)."""

    category = serializers.IntegerField(required=False, min_value=1)
    search = serializers.CharField(required=False, allow_blank=True, max_length=100, trim_whitespace=True)
    seller = serializers.IntegerField(required=False, min_value=1)
    price_min = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, min_value=0)
    price_max = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, min_value=0)
    country = serializers.IntegerField(required=False, min_value=1)
    state = serializers.IntegerField(required=False, min_value=1)
    city = serializers.IntegerField(required=False, min_value=1)
    thana = serializers.IntegerField(required=False, min_value=1)
    ordering = serializers.ChoiceField(required=False, choices=list(ORDERINGS))
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=BuyerPagePagination.max_page_size)

    def validate(self, attrs):
        low, high = attrs.get("price_min"), attrs.get("price_max")
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError({"price_min": "Cannot be higher than price_max."})
        return attrs


class ProductQuerySerializer(_ListQuerySerializer):
    listing_type = serializers.ChoiceField(required=False, choices=Listing.ListingType.choices)
    brand = serializers.IntegerField(required=False, min_value=1)
    in_stock = serializers.BooleanField(required=False)


class GigQuerySerializer(_ListQuerySerializer):
    price_type = serializers.ChoiceField(required=False, choices=ListingSku.PriceType.choices)
    delivery_days_max = serializers.IntegerField(required=False, min_value=0)
    urgent = serializers.BooleanField(required=False)


# ------------------------------------------------------------------------ queryset


def _effective_price(now):
    """SQL twin of ListingSku.effective_price(): the discounted price while the
    discount window is open, otherwise the normal price."""
    window_open = (
        Q(discounted_price__lt=F("price"))
        & (Q(discount_start_date__isnull=True) | Q(discount_start_date__lte=now))
        & (Q(discount_end_date__isnull=True) | Q(discount_end_date__gte=now))
    )
    return Case(
        When(window_open, then=F("discounted_price")), default=F("price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )


def _category_ids_with_descendants(category_id):
    """The category and every sub-category below it (a small reference table: one light query)."""
    children = {}
    for id_, parent in Category.objects.values_list("id", "parent_id"):
        children.setdefault(parent, []).append(id_)
    found, stack = set(), [category_id]
    while stack:
        node = stack.pop()
        if node not in found:
            found.add(node)
            stack.extend(children.get(node, []))
    return found


def _active_skus(price_type=None):
    skus = ListingSku.objects.filter(listing=OuterRef("pk"), is_active=True)
    return skus.filter(price_type=price_type) if price_type else skus


class _PublicListingBase(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = BuyerPagePagination
    scope = Q()
    query_serializer = _ListQuerySerializer

    def base_queryset(self):
        return Listing.objects.filter(
            self.scope, public_seller_listings_q(), status=Listing.Status.APPROVED
        )

    def get_params(self):
        query = self.query_serializer(data=self.request.query_params, partial=True)  # partial: absent booleans stay absent
        query.is_valid(raise_exception=True)
        return query.validated_data

    def filtered(self, params):
        now = timezone.now()
        price_type = params.get("price_type")
        cheapest = _active_skus(price_type).annotate(eff=_effective_price(now)).order_by("eff").values("eff")[:1]
        rows = self.base_queryset().annotate(min_price=Subquery(cheapest))
        rows = rows.filter(min_price__isnull=False)  # nothing to buy: not listed

        if "category" in params:
            rows = rows.filter(category_id__in=_category_ids_with_descendants(params["category"]))
        if params.get("search"):
            term = params["search"]
            rows = rows.filter(
                Q(title__icontains=term) | Q(title_bn__icontains=term)
                | Q(brand__name__icontains=term) | Q(model__icontains=term)
            )
        for key in ("seller", "country", "state", "city", "thana"):
            if key in params:
                rows = rows.filter(**{f"{key}_id": params[key]})
        if "price_min" in params:
            rows = rows.filter(min_price__gte=params["price_min"])
        if "price_max" in params:
            rows = rows.filter(min_price__lte=params["price_max"])
        return rows

    def list_context(self, params):
        return {"price_type": params.get("price_type")}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(getattr(self, "_extra_context", {}))
        return context

    def get_queryset(self):
        params = self.get_params()
        self._extra_context = self.list_context(params)
        rows = self.filtered(params).select_related("category", "brand", "seller")
        rows = rows.prefetch_related(Prefetch("skus", queryset=ListingSku.objects.filter(is_active=True)))
        return rows.order_by(*ORDERINGS[params.get("ordering", "newest")])


# ------------------------------------------------------------------- serializers


class _CategoryBrief(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    name_bn = serializers.CharField()
    slug = serializers.CharField()


def _cheapest(listing, price_type=None):
    """The cheapest active SKU right now (of one price type when asked): the "from" price."""
    skus = [s for s in listing.skus.all() if s.is_active and (price_type is None or s.price_type == price_type)]
    return min(skus, key=lambda s: (s.effective_price(), s.price)) if skus else None


class _PriceFields(serializers.Serializer):
    price = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    def _cheapest(self, obj):
        return _cheapest(obj, self.context.get("price_type"))

    def get_price(self, obj):
        sku = self._cheapest(obj)
        return str(sku.price) if sku else None

    def get_discounted_price(self, obj):
        sku = self._cheapest(obj)
        return str(sku.effective_price()) if sku else None


class _ListingRow(_PriceFields, serializers.ModelSerializer):
    category = _CategoryBrief(read_only=True)
    seller = PublicSellerBriefSerializer(read_only=True)


class PublicProductListSerializer(_ListingRow):
    brand = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "listing_type", "category", "brand", "image_url",
            "price", "discounted_price", "currency", "in_stock", "seller", "created_at",
        ]

    def get_brand(self, obj):
        return {"id": obj.brand_id, "name": obj.brand.name} if obj.brand_id else None

    def get_in_stock(self, obj):
        return any(_available(s) for s in obj.skus.all() if s.is_active)


class PublicGigListSerializer(_ListingRow):
    price_type = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "title_bn", "slug", "category", "image_url", "price", "discounted_price",
            "price_type", "currency", "delivery_days", "urgent", "seller", "created_at",
        ]

    def get_price_type(self, obj):
        sku = self._cheapest(obj)
        return sku.price_type if sku else None


def _available(sku):
    """Stock left on a product SKU (`None` stock = not tracked = available)."""
    return sku.stock_qty is None or sku.stock_qty - sku.reserved_qty > 0


class _PublicMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingMedia
        fields = ["id", "media_type", "media_url"]


class _PublicVariantSerializer(serializers.ModelSerializer):
    attribute = serializers.SerializerMethodField()
    attribute_value = serializers.SerializerMethodField()

    class Meta:
        model = ListingSkuVariant
        fields = ["attribute", "attribute_value"]

    def get_attribute(self, obj):
        return {"id": obj.attribute_id, "name": obj.attribute.name, "name_bn": obj.attribute.name_bn}

    def get_attribute_value(self, obj):
        return {"id": obj.attribute_value_id, "name": obj.attribute_value.name, "name_bn": obj.attribute_value.name_bn}


class _SkuBase(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()
    is_discount_active = serializers.SerializerMethodField()

    def get_discounted_price(self, obj):
        return str(obj.effective_price())

    def get_is_discount_active(self, obj):
        return obj.effective_price() < obj.price


class PublicProductSkuSerializer(_SkuBase):
    variants = _PublicVariantSerializer(many=True, read_only=True)
    in_stock = serializers.SerializerMethodField()
    available_qty = serializers.SerializerMethodField()

    class Meta:
        model = ListingSku
        fields = ["id", "sku", "price", "discounted_price", "is_discount_active", "in_stock", "available_qty", "variants"]

    def get_in_stock(self, obj):
        return _available(obj)

    def get_available_qty(self, obj):
        return None if obj.stock_qty is None else max(obj.stock_qty - obj.reserved_qty, 0)


class PublicGigPackageSerializer(_SkuBase):
    class Meta:
        model = ListingSku
        fields = ["id", "price_type", "price", "discounted_price", "is_discount_active", "description", "description_bn"]


class _PublicTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPriceTier
        fields = ["id", "listing_sku", "min_qty", "max_qty", "price", "discounted_price"]


class _LocationMixin(serializers.Serializer):
    location = serializers.SerializerMethodField()

    def get_location(self, obj):
        return {
            level: ({"id": getattr(obj, f"{level}_id"), "name": getattr(obj, level).name} if getattr(obj, f"{level}_id") else None)
            for level in ("country", "state", "city", "thana")
        }


class PublicProductDetailSerializer(_LocationMixin, PublicProductListSerializer):
    skus = PublicProductSkuSerializer(many=True, read_only=True)
    price_tiers = _PublicTierSerializer(many=True, read_only=True)
    media = _PublicMediaSerializer(many=True, read_only=True)
    measurement = serializers.SerializerMethodField()

    class Meta(PublicProductListSerializer.Meta):
        fields = PublicProductListSerializer.Meta.fields + [
            "description", "description_bn", "model", "origin", "origin_bn", "warranty", "warranty_bn",
            "measurement", "min_order_qty", "condition_note", "condition_note_bn", "attributes",
            "location", "skus", "price_tiers", "media", "updated_at",
        ]

    def get_measurement(self, obj):
        return {"id": obj.measurement_id, "name": obj.measurement.name, "symbol": obj.measurement.symbol} if obj.measurement_id else None


class PublicGigDetailSerializer(_LocationMixin, PublicGigListSerializer):
    packages = PublicGigPackageSerializer(source="skus", many=True, read_only=True)
    media = _PublicMediaSerializer(many=True, read_only=True)

    class Meta(PublicGigListSerializer.Meta):
        fields = PublicGigListSerializer.Meta.fields + [
            "description", "description_bn", "package_includes", "package_includes_bn",
            "available_from", "available_to", "location", "packages", "media", "updated_at",
        ]


# ---------------------------------------------------------------------------- views


class PublicProductListView(_PublicListingBase):
    """`GET /api/v1/public/catalog/products/` — see docs/public-api-guide.md."""

    scope = PRODUCT_SCOPE
    query_serializer = ProductQuerySerializer
    serializer_class = PublicProductListSerializer

    def filtered(self, params):
        rows = super().filtered(params)
        if "listing_type" in params:
            rows = rows.filter(listing_type=params["listing_type"])
        if "brand" in params:
            rows = rows.filter(brand_id=params["brand"])
        if "in_stock" in params:
            in_stock = _active_skus().filter(Q(stock_qty__isnull=True) | Q(stock_qty__gt=F("reserved_qty")))
            rows = rows.filter(Exists(in_stock)) if params["in_stock"] else rows.exclude(Exists(in_stock))
        return rows


class PublicGigListView(_PublicListingBase):
    """`GET /api/v1/public/catalog/gigs/` — see docs/public-api-guide.md."""

    scope = GIG_SCOPE
    query_serializer = GigQuerySerializer
    serializer_class = PublicGigListSerializer

    def filtered(self, params):
        rows = super().filtered(params)
        if "price_type" in params:
            rows = rows.filter(Exists(_active_skus(params["price_type"])))
        if "delivery_days_max" in params:
            rows = rows.filter(delivery_days__isnull=False, delivery_days__lte=params["delivery_days_max"])
        if "urgent" in params:
            rows = rows.filter(urgent=True) if params["urgent"] else rows.exclude(urgent=True)
        return rows


class _PublicListingDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    scope = Q()

    def get_queryset(self):
        skus = Prefetch("skus", queryset=ListingSku.objects.filter(is_active=True).order_by("id"))
        return (
            Listing.objects.filter(self.scope, public_seller_listings_q(), status=Listing.Status.APPROVED)
            .select_related("category", "brand", "seller", "measurement", "country", "state", "city", "thana")
            .prefetch_related(skus, "media")
        )

    def get_object(self):
        listing = super().get_object()
        if not any(s.is_active for s in listing.skus.all()):
            raise NotFound()  # nothing to buy: not public (same rule as the list)
        return listing


class PublicProductDetailView(_PublicListingDetail):
    scope = PRODUCT_SCOPE
    serializer_class = PublicProductDetailSerializer

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "price_tiers", "skus__variants__attribute", "skus__variants__attribute_value"
        )


class PublicGigDetailView(_PublicListingDetail):
    scope = GIG_SCOPE
    serializer_class = PublicGigDetailSerializer
