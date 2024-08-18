# Generated by Django 5.0.6 on 2024-06-21 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_rename_product_image_variant_image_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='variant',
            name='is_available',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='variant_image',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
