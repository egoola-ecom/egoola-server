from django.db import migrations


def move_price_type_to_skus(apps, schema_editor):
    """Step 2 of 3 (data only). The listing's old `price_type` / `hourly_rate`
    become the price type of the listing's SKU.

    - A service listing with no `posted_by_role` is a gig (`seller_offer`).
    - The first active SKU (else the first SKU) of a service listing takes the
      price type: `hourly` (its price becomes the old hourly rate when there was
      one), otherwise `fixed`.
    - A gig has at most one SKU per price type and no options, so the other SKUs
      of a gig are hidden (`is_active = false`); nothing is deleted.

    One-way in practice: an hourly service's SKU price is replaced by the old hourly
    rate (the previous price is not kept), so the reverse step restores the price
    type and hourly rate but not the old SKU price.
    """
    Listing = apps.get_model("catalog", "Listing")
    ListingSku = apps.get_model("catalog", "ListingSku")

    Listing.objects.filter(catalog_type="service", posted_by_role__isnull=True).update(posted_by_role="seller_offer")

    for listing in Listing.objects.filter(catalog_type="service").iterator():
        skus = list(ListingSku.objects.filter(listing=listing).order_by("-is_active", "id"))
        if not skus:
            continue
        first, others = skus[0], skus[1:]
        price_type = "hourly" if listing.price_type == "hourly" else "fixed"
        if price_type == "hourly" and listing.hourly_rate is not None:
            first.discounted_price = min(first.discounted_price, listing.hourly_rate)
            first.price = listing.hourly_rate
        first.price_type = price_type
        is_gig = listing.posted_by_role == "seller_offer"
        first.save()
        if is_gig:
            for sku in others:
                if sku.is_active:
                    sku.is_active = False
                    sku.save(update_fields=["is_active"])


def move_price_type_back(apps, schema_editor):
    Listing = apps.get_model("catalog", "Listing")
    ListingSku = apps.get_model("catalog", "ListingSku")
    for listing in Listing.objects.filter(catalog_type="service").iterator():
        sku = ListingSku.objects.filter(listing=listing, price_type__isnull=False).order_by("id").first()
        if sku is None:
            continue
        listing.price_type = "hourly" if sku.price_type == "hourly" else "fixed"
        if sku.price_type == "hourly":
            listing.hourly_rate = sku.price
        listing.save(update_fields=["price_type", "hourly_rate"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_gig_sku_fields_and_thumbnail"),
    ]

    operations = [
        migrations.RunPython(move_price_type_to_skus, move_price_type_back),
    ]
