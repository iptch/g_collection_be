# Generated by Django 4.2.3 on 2023-09-30 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_ownership_otp_valid_to_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ownership',
            name='otp_valid_to',
            field=models.DateTimeField(null=True),
        ),
    ]
