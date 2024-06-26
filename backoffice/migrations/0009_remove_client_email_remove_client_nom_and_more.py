# Generated by Django 5.0.6 on 2024-06-17 19:52

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0008_remove_commande_user_commande_client_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="client",
            name="email",
        ),
        migrations.RemoveField(
            model_name="client",
            name="nom",
        ),
        migrations.RemoveField(
            model_name="client",
            name="prenom",
        ),
        migrations.AddField(
            model_name="client",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
                verbose_name="Utilisateur",
            ),
        ),
    ]
