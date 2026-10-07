"""
Categories (DB Redesign doc, Section 3.4) and Catalog / Listings (Section 3.5).

`Category` is one self-referencing tree for both products and services
(replacing two separate three-level legacy trees). `Listing` is the single
table behind every one of the six legacy product-shop formats plus the old
`services` table (replacing products/used_malls/village_products/
retail_shops/wholesales/brand_walls/services/product_images/service_images/
documents).
"""

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import ActorType, AuditedModel


class ActiveListingManager(models.Manager):
    """Default manager for Listing — every ordinary query (list, retrieve,
    filter) should never see a soft-deleted row, so the exclusion lives
    here once instead of being repeated at every call site."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Category(AuditedModel):
    class CatalogType(models.TextChoices):
        PRODUCT = "product", "Product"
        SERVICE = "service", "Service"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children", db_column="parentId"
    )
    type = models.CharField(max_length=10, choices=CatalogType.choices)
    name = models.CharField(max_length=255)
    name_bn = models.CharField(db_column="nameBn", max_length=255)
    slug = models.SlugField(max_length=255)
    image_path = models.CharField(db_column="imagePath", max_length=255, null=True, blank=True)
    image_url = models.URLField(db_column="imageUrl", max_length=500, null=True, blank=True)
    sort_order = models.IntegerField(db_column="sortOrder", default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(fields=["type", "slug"], name="unique_category_slug_per_type")
        ]

    def __str__(self):
        return self.name


class Measurement(AuditedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    symbol = models.CharField(max_length=20)

    class Meta:
        db_table = "measurements"
        ordering = ["name"]

    def __str__(self):
        return self.symbol


class Brand(AuditedModel):
    """Admin-managed brand list — a Listing picks from here instead of
    typing a free-text brand name."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    is_active = models.BooleanField(db_column="isActive", default=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Listing(AuditedModel):
    class CatalogType(models.TextChoices):
        PRODUCT = "product", "Product"
        SERVICE = "service", "Service"

    class ListingType(models.TextChoices):
        GENERAL = "general", "General"
        USED = "used", "Used"
        VILLAGE = "village", "Village"
        RETAIL = "retail", "Retail"
        WHOLESALE = "wholesale", "Wholesale"
        BRAND = "brand", "Brand"

    class PostedByRole(models.TextChoices):
        SELLER_OFFER = "seller_offer", "Seller Offer"
        BUYER_REQUEST = "buyer_request", "Buyer Request"

    class PriceType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        HOURLY = "hourly", "Hourly"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"

    # Both are optional (an Admin can create a listing owned by neither);
    # when set, at most one of the two is, matching posted_by_role — see
    # the correctness note in DB Redesign doc Section 3.5.
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.CASCADE, null=True, blank=True, related_name="listings",
        db_column="sellerId",
    )
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="posted_listings",
        db_column="buyerId",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="listings", db_column="categoryId"
    )
    catalog_type = models.CharField(db_column="catalogType", max_length=10, choices=CatalogType.choices)
    listing_type = models.CharField(
        db_column="listingType", max_length=10, choices=ListingType.choices, null=True, blank=True
    )
    posted_by_role = models.CharField(
        db_column="postedByRole", max_length=15, choices=PostedByRole.choices, null=True, blank=True
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()

    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, null=True, blank=True, related_name="listings", db_column="brandId"
    )
    model = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    origin = models.CharField(max_length=255, null=True, blank=True)
    warranty = models.CharField(max_length=255, null=True, blank=True)

    # `price` is always the original/actual price; `discounted_price` is the
    # price actually charged (price=150, discounted=120). When no discount is
    # given it equals `price` — save() fills it in, so it is never null.
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discounted_price = models.DecimalField(
        db_column="discountedPrice", max_digits=12, decimal_places=2, blank=True
    )
    currency = models.CharField(max_length=8, default="BDT")

    # Service side
    price_type = models.CharField(
        db_column="priceType", max_length=10, choices=PriceType.choices, null=True, blank=True
    )
    hourly_rate = models.DecimalField(
        db_column="hourlyRate", max_digits=12, decimal_places=2, null=True, blank=True
    )
    delivery_days = models.IntegerField(db_column="deliveryDays", null=True, blank=True)
    urgent = models.BooleanField(null=True, blank=True)
    package_includes = models.TextField(db_column="packageIncludes", null=True, blank=True)
    available_from = models.DateTimeField(db_column="availableFrom", null=True, blank=True)
    available_to = models.DateTimeField(db_column="availableTo", null=True, blank=True)

    # Product side
    min_order_qty = models.IntegerField(db_column="minOrderQty", null=True, blank=True)
    stock_qty = models.BigIntegerField(db_column="stockQty", null=True, blank=True)
    measurement = models.ForeignKey(
        Measurement, on_delete=models.SET_NULL, null=True, blank=True, db_column="measurementId"
    )
    colors = models.JSONField(null=True, blank=True)
    sizes = models.JSONField(null=True, blank=True)
    reserved_qty = models.IntegerField(db_column="reservedQty", null=True, blank=True)
    condition_note = models.TextField(db_column="conditionNote", null=True, blank=True)
    attributes = models.JSONField(null=True, blank=True)

    country = models.ForeignKey(
        "geography.Country", on_delete=models.SET_NULL, null=True, blank=True, db_column="countryId"
    )
    state = models.ForeignKey(
        "geography.State", on_delete=models.SET_NULL, null=True, blank=True, db_column="stateId"
    )
    city = models.ForeignKey(
        "geography.City", on_delete=models.SET_NULL, null=True, blank=True, db_column="cityId"
    )
    thana = models.ForeignKey(
        "geography.Thana", on_delete=models.SET_NULL, null=True, blank=True, db_column="thanaId"
    )

    status = models.CharField(max_length=18, choices=Status.choices, default=Status.DRAFT)
    # Always holds the note for the *current* status only — never a
    # history of past notes (that lives in ListingStatusChangeLog instead).
    # Required by validate() when status is rejected/changes_requested,
    # optional otherwise; null whenever no note was given for that event.
    note = models.TextField(null=True, blank=True)

    deleted_at = models.DateTimeField(db_column="deletedAt", null=True, blank=True)

    objects = ActiveListingManager()
    # Unfiltered — only for checking slug uniqueness against every row,
    # soft-deleted included, since the DB's unique constraint on `slug`
    # doesn't care that a row is soft-deleted.
    all_objects = models.Manager()

    class Meta:
        db_table = "listings"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["colors"], name="listings_colors_gin"),
            GinIndex(fields=["sizes"], name="listings_sizes_gin"),
            GinIndex(fields=["attributes"], name="listings_attributes_gin"),
        ]

    def save(self, *args, **kwargs):
        if self.discounted_price is None:
            self.discounted_price = self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ListingPriceTier(AuditedModel):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="price_tiers", db_column="listingId"
    )
    min_qty = models.IntegerField(db_column="minQty")
    max_qty = models.IntegerField(db_column="maxQty", null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    # Equals `price` when no discount is given — save() fills it in.
    discounted_price = models.DecimalField(
        db_column="discountedPrice", max_digits=12, decimal_places=2, blank=True
    )

    class Meta:
        db_table = "listingPriceTiers"
        ordering = ["min_qty"]

    def save(self, *args, **kwargs):
        if self.discounted_price is None:
            self.discounted_price = self.price
        super().save(*args, **kwargs)


class ListingMedia(AuditedModel):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media", db_column="listingId")
    media_type = models.CharField(db_column="mediaType", max_length=10, choices=MediaType.choices)
    media_path = models.CharField(db_column="mediaPath", max_length=255)
    media_url = models.URLField(db_column="mediaUrl", max_length=500)

    class Meta:
        db_table = "listingMedia"
        verbose_name_plural = "listing media"


class ListingStatusChangeLog(models.Model):
    """Append-only history of every status change on a Listing — who
    changed it, to what, and why (for a rejection or a changes-requested).
    Written once on Listing creation and again on every update that
    changes status; never updated or deleted afterwards, so this isn't an
    AuditedModel — there's no updated_by/updated_at to track on a row that
    never changes after it's written. Mirrors SellerVerificationLog."""

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="status_change_logs", db_column="listingId"
    )
    status = models.CharField(max_length=18, choices=Listing.Status.choices)
    note = models.TextField(null=True, blank=True)

    created_by = models.BigIntegerField(db_column="createdBy", null=True, blank=True)
    creator_type = models.CharField(
        db_column="creatorType", max_length=10, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    creator_name = models.CharField(db_column="creatorName", max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(db_column="createdAt", auto_now_add=True)

    class Meta:
        db_table = "listingStatusChangeLogs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Listing #{self.listing_id} -> {self.status}"
