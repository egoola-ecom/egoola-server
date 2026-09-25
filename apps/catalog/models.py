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

from apps.core.models import AuditedModel


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
    slug = models.SlugField(max_length=255, unique=True)
    image_path = models.CharField(db_column="imagePath", max_length=255, null=True, blank=True)
    image_url = models.URLField(db_column="imageUrl", max_length=500, null=True, blank=True)
    sort_order = models.IntegerField(db_column="sortOrder", default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Measurement(AuditedModel):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)

    class Meta:
        db_table = "measurements"
        ordering = ["name"]

    def __str__(self):
        return self.symbol


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

    # Exactly one of seller/buyer is set, depending on posted_by_role — see
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

    brand = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    origin = models.CharField(max_length=255, null=True, blank=True)
    warranty = models.CharField(max_length=255, null=True, blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(db_column="oldPrice", max_digits=12, decimal_places=2, null=True, blank=True)
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

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        db_table = "listings"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["colors"], name="listings_colors_gin"),
            GinIndex(fields=["sizes"], name="listings_sizes_gin"),
            GinIndex(fields=["attributes"], name="listings_attributes_gin"),
        ]

    def __str__(self):
        return self.title


class ListingPriceTier(AuditedModel):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="price_tiers", db_column="listingId"
    )
    min_qty = models.IntegerField(db_column="minQty")
    max_qty = models.IntegerField(db_column="maxQty", null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "listingPriceTiers"
        ordering = ["min_qty"]


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
