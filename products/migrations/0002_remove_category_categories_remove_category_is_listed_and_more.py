# Generated by Django 5.0.6 on 2024-06-14 06:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='categories',
        ),
        migrations.RemoveField(
            model_name='category',
            name='is_listed',
        ),
        migrations.AddField(
            model_name='category',
            name='category_name',
            field=models.CharField(default='Uncategorized', max_length=100),
        ),
        migrations.AddField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='category_images/'),
        ),
        migrations.AddField(
            model_name='category',
            name='total_products',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
