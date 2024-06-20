import datetime
from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.core.validators import RegexValidator

class Client(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    # nom = models.CharField(max_length=100, blank=True, null=True)
    # prenom = models.CharField(max_length=100, blank=True, null=True)
    # email = models.CharField(max_length=100, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True, validators=[
            RegexValidator(
                regex='^\\+?1?\\d{9,15}$',  # Exemple de regex pour valider un numéro international
                message="Le numéro de téléphone doit être entré au format '+999999999'. Jusqu'à 15 chiffres autorisés."
            )
        ])

    def __str__(self):
        return f"{self.user}"
        # return f"{self.nom} {self.prenom}"
    
class Livreur(models.Model):
    # nom = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    statut = models.CharField(max_length=50, choices=[('disponible', 'disponible'), ('en_cours_de_livraison', 'En cours de livraison'), ('indisponible', 'indisponible')], blank=True, null=True)
    position_geo = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user}"
        # return self.nom
    

class Produit(models.Model):
    nom_produit = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    prix = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, default=0)
    type_produit = models.CharField(max_length=255, choices=[('plat', 'Plat'), ('dessert', 'Dessert'),('boissons', 'Boissons'),('pizza', 'Pizza')], default='plat', blank=True, null=True)
    image = models.ImageField(upload_to='produits/', blank=True, null=True)
    statut = models.CharField(max_length=20, choices=[('disponible', 'Disponible'), ('indisponible', 'Indisponible'),], default='disponible')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de Création")

    def __str__(self):
        return self.nom_produit

@receiver(post_delete, sender=Produit)
def submission_delete(sender, instance, **kwargs):
    # Supprime le fichier après la suppression de l'instance du modèle
    if instance.image:
        default_storage.delete(instance.image.path)

class Commande(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    livreur = models.ForeignKey('Livreur', on_delete=models.SET_NULL, null=True, blank=True)
    date_commande = models.DateTimeField(blank=True, null=True)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    statut = models.CharField(max_length=50, choices=[('en_cours', 'En cours'), ('prise_en_charge', 'Prise en charge'), ('en_cours_de_livraison', 'En cours de livraison'), ('livree', 'livrée')], default='en_cours', blank=True, null=True)
    frais_livraison = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    temps_estime_livraison = models.TimeField(blank=True, null=True)

    def __str__(self):
        return f"Commande {self.id} - {self.statut}"

class CommandeProduit(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    quantite = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.produit.nom_produit} x {self.quantite}"

class Paiement(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    methode_paiement = models.CharField(max_length=10, choices=[('', ''),('stripe', 'Stripe'), ('especes', 'Espèces')], blank=True, null=True)
    statut_paiement = models.CharField(max_length=10, choices=[('en_attente', 'En attente'), ('paye', 'Payé'), ('annule', 'Annulé')], default='en_attente', blank=True, null=True)
    date_paiement = models.DateTimeField(blank=True, null=True)
    payment_token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token de Paiement")

    def __str__(self):
        return f"Paiement {self.id} - {self.statut_paiement}"
