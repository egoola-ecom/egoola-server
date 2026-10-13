import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3 of 3: one SKU per price type on a listing (database rule), the
    same-title rule per type, and the old `priceType` / `hourlyRate` columns
    leave `listings`."""

    dependencies = [
        ("catalog", "0012_gig_data_backfill"),
    ]

    operations = [
        # The same-title rule now applies per type: a seller may have a product
        # and a gig with the same title.
        migrations.RemoveConstraint(model_name="listing", name="unique_listing_title_per_seller"),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("title"), models.F("seller"), models.F("catalog_type"),
                condition=models.Q(("deleted_at__isnull", True), ("seller__isnull", False)),
                name="unique_listing_title_per_seller",
            ),
        ),
        migrations.AddConstraint(
            model_name="listingsku",
            constraint=models.UniqueConstraint(
                condition=models.Q(("price_type__isnull", False)),
                fields=("listing", "price_type"),
                name="unique_sku_price_type_per_listing",
            ),
        ),
        migrations.RemoveField(model_name="listing", name="price_type"),
        migrations.RemoveField(model_name="listing", name="hourly_rate"),
    ]
