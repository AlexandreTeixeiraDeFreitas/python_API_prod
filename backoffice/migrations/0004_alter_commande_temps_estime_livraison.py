# Generated by Django 5.0.6 on 2024-06-17 13:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0003_alter_commande_temps_estime_livraison"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commande",
            name="temps_estime_livraison",
            field=models.TimeField(blank=True, null=True),
        ),
    ]