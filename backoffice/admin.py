from django.contrib import admin
from .models import Client, Commande, CommandeProduit, Produit, Livreur, Paiement

admin.site.register(Client)
admin.site.register(Commande)
admin.site.register(CommandeProduit)
admin.site.register(Produit)
admin.site.register(Livreur)
admin.site.register(Paiement)