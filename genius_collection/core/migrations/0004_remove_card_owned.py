# Generated by Django 4.2.3 on 2023-09-29 09:56

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_card_owned"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="card",
            name="owned",
        ),
    ]
