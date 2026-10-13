from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1 of 3 (schema only, nothing removed yet): the listing thumbnail,
    and the gig fields on listing SKUs (price type, descriptions)."""

    dependencies = [
        ("catalog", "0010_listing_pending_requires_requested_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="image_path",
            field=models.CharField(blank=True, db_column="imagePath", max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="image_url",
            field=models.URLField(blank=True, db_column="imageUrl", max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="listingsku",
            name="price_type",
            field=models.CharField(
                blank=True, db_column="priceType", null=True, max_length=10,
                choices=[
                    ("fixed", "Fixed"), ("hourly", "Hourly"), ("daily", "Daily"),
                    ("weekly", "Weekly"), ("monthly", "Monthly"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="listingsku",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listingsku",
            name="description_bn",
            field=models.TextField(blank=True, db_column="descriptionBn", null=True),
        ),
    ]
