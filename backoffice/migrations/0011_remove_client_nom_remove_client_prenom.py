# Generated by Django 5.0.6 on 2024-06-17 20:35

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0010_client_nom_client_prenom"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="client",
            name="nom",
        ),
        migrations.RemoveField(
            model_name="client",
            name="prenom",
        ),
    ]