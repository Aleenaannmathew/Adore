# Generated by Django 5.0.6 on 2024-07-04 05:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_alter_variant_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='variant',
            name='max_quantity_per_person',
            field=models.PositiveIntegerField(default=10),
        ),
    ]
