from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_alter_category_slug_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="measurement",
            name="slug",
            field=models.SlugField(default="", max_length=100, unique=True),
            preserve_default=False,
        ),
    ]
