# Generated by Django 5.0.6 on 2024-06-17 18:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0005_produit_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commande",
            name="statut",
            field=models.CharField(
                blank=True,
                choices=[
                    ("en_cours", "En cours"),
                    ("prise_en_charge", "Prise en charge"),
                    ("livree", "livrée"),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
