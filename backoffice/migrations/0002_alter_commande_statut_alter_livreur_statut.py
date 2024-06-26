# Generated by Django 5.0.6 on 2024-06-17 12:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commande",
            name="statut",
            field=models.CharField(
                blank=True,
                choices=[
                    ("en_attente", "En attente"),
                    ("paye", "Payé"),
                    ("annule", "Annulé"),
                ],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="livreur",
            name="statut",
            field=models.CharField(
                blank=True,
                choices=[
                    ("disponible", "disponible"),
                    ("indisponible", "indisponible"),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
