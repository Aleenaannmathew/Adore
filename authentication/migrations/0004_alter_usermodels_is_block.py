# Generated by Django 5.0.6 on 2024-06-11 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_remove_usermodels_otp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usermodels',
            name='is_block',
            field=models.BooleanField(default=False),
        ),
    ]
