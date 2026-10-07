from django.db import migrations, models
from django.db.models import F


def backfill(apps, schema_editor):
    for name in ("Listing", "ListingPriceTier"):
        model = apps.get_model("catalog", name)
        model._base_manager.filter(discounted_price__isnull=True).update(discounted_price=F("price"))


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_brand_discounted_price'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='listing',
            name='discounted_price',
            field=models.DecimalField(blank=True, db_column='discountedPrice', decimal_places=2, max_digits=12),
        ),
        migrations.AlterField(
            model_name='listingpricetier',
            name='discounted_price',
            field=models.DecimalField(blank=True, db_column='discountedPrice', decimal_places=2, max_digits=12),
        ),
    ]
