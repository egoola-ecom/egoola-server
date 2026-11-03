from django.db import migrations


def seed_cod(apps, schema_editor):
    """Checkout needs a real gateway id to point at; COD is the only one
    built for now (see docs/buyer/buyer-api-guide.md)."""
    PaymentGateway = apps.get_model("orders", "PaymentGateway")
    PaymentGateway.objects.get_or_create(
        slug="cash-on-delivery", defaults={"name": "Cash on Delivery", "is_active": True},
    )


def unseed_cod(apps, schema_editor):
    PaymentGateway = apps.get_model("orders", "PaymentGateway")
    PaymentGateway.objects.filter(slug="cash-on-delivery").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_paymentgateway_cart_buyer_type_order_rejected_reason_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_cod, unseed_cod),
    ]
