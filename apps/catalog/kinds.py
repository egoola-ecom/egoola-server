"""
The three kinds of listing and which fields belong to which.

All three are rows of the one `listings` table, but each has its own API:

- **product**: `catalog_type = product`. `/catalog/listings/` (admin) and
  `/seller/listings/` (seller).
- **gig**: `catalog_type = service`, `posted_by_role = seller_offer`. A seller's
  service offer. `/catalog/gigs/` (admin) and `/seller/gigs/` (seller).
- **job**: `catalog_type = service`, `posted_by_role = buyer_request`. A buyer's
  request for work. Until the Job step is built, an admin manages these through
  `/catalog/listings/`.

A gig is priced on its SKUs: one SKU per price type (hourly, daily, weekly,
monthly, fixed). The buyer chooses the duration when ordering (it is on the order item). A product is priced on SKUs that carry
options (size, colour) and stock.
"""

PRODUCT = "product"
GIG = "gig"
JOB = "job"

# Listing fields that only make sense for a product.
PRODUCT_ONLY_FIELDS = (
    "listing_type", "brand", "model", "origin", "origin_bn", "warranty", "warranty_bn",
    "measurement", "min_order_qty", "condition_note", "condition_note_bn", "attributes",
)

# Listing fields that only make sense for a service (a gig or a job).
SERVICE_ONLY_FIELDS = (
    "delivery_days", "urgent", "package_includes", "package_includes_bn", "available_from", "available_to",
)

# SKU fields that only a gig uses.
GIG_SKU_FIELDS = ("price_type", "description", "description_bn")
