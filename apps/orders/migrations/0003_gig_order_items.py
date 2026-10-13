from django.db import migrations, models


class Migration(migrations.Migration):
    """Gigs and the order amounts.

    - A gig has no quantity: cart and order item `qty` are optional, and an item
      carries the `duration` the buyer chose (hours, days, weeks, months).
    - `orderItems` remembers the gig's price type (`priceTypeSnapshot`) and gets a
      `total` (original price x qty, or rate x duration). `subtotal` stays: the same
      amount at the price actually charged. `color`, `size` and `status` leave
      `orderItems` (the SKU's options say which size / colour; there is no item status).
    - `orders` gets `payable`: what the buyer actually has to pay.
    """

    dependencies = [
        ("orders", "0002_listing_skus_and_attributes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cartitem", name="qty", field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="duration",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="orderitem", name="qty", field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="duration",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="price_type_snapshot",
            field=models.CharField(blank=True, db_column="priceTypeSnapshot", max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="total",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.RunSQL(
            sql='UPDATE "orderItems" SET "total" = "subtotal"',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveField(model_name="orderitem", name="color"),
        migrations.RemoveField(model_name="orderitem", name="size"),
        migrations.RemoveField(model_name="orderitem", name="status"),
        migrations.AddField(
            model_name="order",
            name="payable",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.RunSQL(
            sql='UPDATE "orders" SET "payable" = "subtotal" + "deliveryCost" - "discount"',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
