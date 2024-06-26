# Generated by Django 5.0.6 on 2024-06-17 19:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0007_remove_commande_client_customuser_commande_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="commande",
            name="user",
        ),
        migrations.AddField(
            model_name="commande",
            name="client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="backoffice.client",
            ),
        ),
        migrations.DeleteModel(
            name="CustomUser",
        ),
    ]
