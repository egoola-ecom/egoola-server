import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_remove_listing_moderation_note_listing_note_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_by', models.BigIntegerField(blank=True, db_column='createdBy', null=True)),
                ('creator_type', models.CharField(choices=[('admin', 'Admin'), ('seller', 'Seller'), ('user', 'User'), ('system', 'System')], db_column='creatorType', default='system', max_length=10)),
                ('creator_name', models.CharField(blank=True, db_column='creatorName', max_length=255, null=True)),
                ('updated_by', models.BigIntegerField(blank=True, db_column='updatedBy', null=True)),
                ('updater_type', models.CharField(blank=True, choices=[('admin', 'Admin'), ('seller', 'Seller'), ('user', 'User'), ('system', 'System')], db_column='updaterType', max_length=10, null=True)),
                ('updater_name', models.CharField(blank=True, db_column='updaterName', max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='createdAt')),
                ('updated_at', models.DateTimeField(auto_now=True, db_column='updatedAt')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('is_active', models.BooleanField(db_column='isActive', default=True)),
            ],
            options={
                'db_table': 'brands',
                'ordering': ['name'],
            },
        ),
        # brand was free text; it becomes a FK to brands. No data is carried
        # over — free-text values have no matching Brand row to point at.
        migrations.RemoveField(
            model_name='listing',
            name='brand',
        ),
        migrations.AddField(
            model_name='listing',
            name='brand',
            field=models.ForeignKey(blank=True, db_column='brandId', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='listings', to='catalog.brand'),
        ),
        migrations.RenameField(
            model_name='listing',
            old_name='old_price',
            new_name='discounted_price',
        ),
        migrations.AlterField(
            model_name='listing',
            name='discounted_price',
            field=models.DecimalField(blank=True, db_column='discountedPrice', decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='listingpricetier',
            name='discounted_price',
            field=models.DecimalField(blank=True, db_column='discountedPrice', decimal_places=2, max_digits=12, null=True),
        ),
    ]
