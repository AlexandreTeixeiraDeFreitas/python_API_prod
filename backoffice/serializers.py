from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils.timezone import now
from .models import Client, Commande, CommandeProduit, Produit, Livreur, Paiement
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from decimal import Decimal
import requests

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        read_only_fields = ['id']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'password': {'write_only': True, 'required': True}
        }

    def validate_username(self, value):
        # Ignorer la validation si le nom d'utilisateur n'a pas changé
        if self.instance and self.instance.username == value:
            return value

        # Vérifier si le nom d'utilisateur existe déjà
        if User.objects.filter(username=value).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return value

    def validate_email(self, value):
        # Ignorer la validation si l'email n'a pas changé
        if self.instance and self.instance.email == value:
            return value

        # Vérifier si l'email existe déjà
        if User.objects.filter(email=value).exists():
            raise ValidationError("Cette adresse email est déjà utilisée.")
        return value

    def create(self, validated_data):
        # Créer l'utilisateur tout en cryptant le mot de passe
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
    
    def update(self, instance, validated_data):
        # Mise à jour des champs utilisateur avec la possibilité de changer le mot de passe
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)

        # Vérifie si un nouveau mot de passe a été fourni
        password = validated_data.get('password')
        if password:
            instance.set_password(password)

        instance.save()
        return instance


def verifier_adresse(adresse):
    """Utilise l'API de l'adresse pour vérifier l'exactitude d'une adresse donnée."""
    url = "https://api-adresse.data.gouv.fr/search"
    params = {'q': adresse, 'limit': 1}  # Limite à un résultat
    response = requests.get(url, params=params)
    data = response.json()
    return data

class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Client
        fields = '__all__'

    def validate(self, data):
        """
        Vérifie que l'utilisateur connecté n'a pas déjà un client et que l'adresse et le téléphone sont présents.
        """
        request = self.context.get('request')
        if request and request.method == 'POST':
            existing_client = Client.objects.filter(user=request.user).exists()
            if existing_client:
                raise ValidationError("Un client est déjà associé à cet utilisateur.")

        if 'adresse' in data and not data['adresse']:
            raise ValidationError("L'adresse ne peut pas être vide.")
        if 'telephone' in data and not data['telephone']:
            raise ValidationError("Le numéro de téléphone ne peut pas être vide.")

        return data

    def validate_adresse(self, value):
        """ Valide que l'adresse est non seulement remplie mais aussi correcte selon l'API."""
        if not value:
            raise serializers.ValidationError("Une adresse est requise.")
        
        # Vérifier l'adresse via l'API
        data = verifier_adresse(value)
        if not data['features']:
            raise serializers.ValidationError("Adresse non valide ou introuvable.")
        
        # Vous pouvez ici choisir de retourner les données complètes de l'API ou simplement la valeur validée
        adresse_complete = data['features'][0]['properties']['label']
        return adresse_complete  # Retourne l'adresse validée et formatée par l'API

    def validate_telephone(self, value):
        """ Valide que le téléphone n'est pas vide. """
        if not value:
            raise serializers.ValidationError("Un numéro de téléphone est requis.")
        return value

    def create(self, validated_data):
        """
        Crée un client, en s'assurant que l'utilisateur est connecté.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return Client.objects.create(user=user, **validated_data)
        else:
            raise ValidationError("L'utilisateur doit être connecté pour créer un client.")
        
class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = '__all__'
        
class LivreurSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Livreur
        fields = '__all__'
        
class CommandeProduitSerializer(serializers.ModelSerializer):
    # commande_detail = CommandeSerializer(source='commande', read_only=True)  # Utilisé pour la lecture
    # commande = serializers.PrimaryKeyRelatedField(queryset=Commande.objects.all(), write_only=True)  # Utilisé pour l'écriture

    produit_detail = ProduitSerializer(source='produit', read_only=True)
    produit = serializers.PrimaryKeyRelatedField(queryset=Produit.objects.all(), write_only=True)

    # commande = CommandeSerializer(read_only=True)
    # produit = ProduitSerializer(read_only=True)
    
    class Meta:
        model = CommandeProduit
        fields = '__all__'
        extra_kwargs = {
            # 'commande': {'write_only': True, 'required': True}
            'produit': {'write_only': True}
        }

    def validate(self, data):
        # Vérifier que le produit est spécifié
        if 'produit' not in data or not data['produit']:
            raise serializers.ValidationError("Le produit est obligatoire.")

        # Vérifier que la quantité est spécifiée
        if 'quantite' not in data or not data['quantite']:
            raise serializers.ValidationError("La quantité est obligatoire.")

        # Vérifier que la commande est spécifiée
        if 'commande' not in data or not data['commande']:
            raise serializers.ValidationError("La commande est obligatoire.")

        return data

    def validate_produit(self, value):
        # Vérifie que le produit est disponible avant de l'ajouter à la commande
        if value.statut != 'disponible':
            raise ValidationError("Ce produit n'est pas disponible pour le moment.")
        return value

    def update_instance_total(self, instance, created=False):
        if instance.commande.montant_total is None:
            instance.commande.montant_total = Decimal('0.00')

        amount_change = instance.quantite * instance.produit.prix
        if created:
            instance.commande.montant_total += amount_change
        else:
            # Recalculer le total en parcourant tous les produits de la commande
            total = sum(cp.quantite * cp.produit.prix for cp in instance.commande.commandeproduit_set.all())
            instance.commande.montant_total = total

        # Mise à jour des frais de livraison si le montant total dépasse 19.99
        if instance.commande.montant_total > Decimal('19.99'):
            instance.commande.frais_livraison = Decimal('0.00')
        else:
            # Rétablir les frais de livraison par défaut si nécessaire
            instance.commande.frais_livraison = Decimal('5.00')

        paiement = Paiement.objects.get(commande=instance.commande)
        if paiement:
            paiement.montant = instance.commande.montant_total + instance.commande.frais_livraison
            instance.commande.paiement = paiement
            paiement.save()
            
        instance.commande.save()

    def check_payment_and_status(self, commande):
        # Récupérer un paiement existant ou en créer un nouveau si nécessaire
        paiement, created = Paiement.objects.get_or_create(
            commande=commande,
            defaults={
                'montant': commande.montant_total + commande.frais_livraison,  # Définir le montant total initial
                'methode_paiement': '',  # Vous devrez spécifier une méthode par défaut ou la définir plus tard
                'statut_paiement': 'en_attente',  # Définir le statut initial
                'date_paiement': now()  # Fixer la date du paiement à l'instant actuel
            }
        )
        
        # Vérifie si un objet paiement existe et si les conditions de statut sont remplies
        
        if paiement and (
            paiement.statut_paiement == 'paye' or
            commande.statut in ['prise_en_charge', 'en_cours_de_livraison', 'livree']):
            raise ValidationError("Modifications non autorisées pour les commandes en cours de traitement ou payées.")

    def create(self, validated_data):
        # Vérifier les conditions de paiement et de statut de la commande
        commande = validated_data.get('commande')
        self.check_payment_and_status(commande)

        # Valider la disponibilité du produit
        produit = validated_data.get('produit')
        self.validate_produit(produit)

        # Valider que le produit n'est pas déjà dans la commande
        if CommandeProduit.objects.filter(commande=commande, produit=produit).exists():
            raise serializers.ValidationError("Ce produit est déjà inclus dans la commande.")

        # Créer l'instance après validation
        instance = super().create(validated_data)
        self.update_instance_total(instance, created=True)
        
        return instance

    def update(self, instance, validated_data):
        # Vérifier les conditions de paiement et de statut de la commande
        self.check_payment_and_status(instance.commande)

        # Valider la disponibilité du produit
        produit = validated_data.get('produit', instance.produit)
        self.validate_produit(produit)

        # Mettre à jour l'instance après validation
        instance = super().update(instance, validated_data)
        self.update_instance_total(instance)
        return instance

    @receiver(pre_delete, sender=CommandeProduit)
    def adjust_command_on_delete(sender, instance, **kwargs):

        # Diminuer le montant total de la commande
        commande = instance.commande
        produit_price = instance.produit.prix
        quantity = instance.quantite
        commande.montant_total -= produit_price * quantity

        # Mise à jour des frais de livraison
        if commande.montant_total > Decimal('19.99'):
            commande.frais_livraison = Decimal('0.00')
        else:
            commande.frais_livraison = Decimal('5.00')

        paiement = Paiement.objects.get(commande=commande)
        if not paiement:
            paiement.montant = commande.montant_total + commande.frais_livraison
            commande.paiement = paiement
            paiement.save()

        commande.save()

class CommandeSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    livreur = LivreurSerializer(read_only=True)
    produits = CommandeProduitSerializer(source='commandeproduit_set', many=True, read_only=True)

    class Meta:
        model = Commande
        fields = '__all__'
        read_only_fields = ('date_commande', 'frais_livraison', 'montant_total', 'temps_estime_livraison')  # Rend ces champs en lecture seule

    def create(self, validated_data):
        user = self.context['request'].user
        
        # Trouver le client associé à l'utilisateur
        client = Client.objects.get(user=user)
        
        # Trouver un livreur disponible
        try:
            livreur = Livreur.objects.filter(statut='disponible').first()
            if not livreur:
                raise ValidationError("Aucun livreur disponible actuellement.")
        except Livreur.DoesNotExist:
            raise ValidationError("Erreur lors de la recherche d'un livreur disponible.")
        
        # Définir les valeurs par défaut
        validated_data['client'] = client
        validated_data['livreur'] = livreur
        validated_data['date_commande'] = now()
        validated_data['statut'] = 'en_cours'
        validated_data['frais_livraison'] = 5.00
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        new_statut = validated_data.get('statut', instance.statut)

        # Définir les transitions de statut autorisées
        valid_transitions = {
            'en_cours': ['prise_en_charge', 'en_cours'],
            'prise_en_charge': ['en_cours_de_livraison', 'prise_en_charge'],
            'en_cours_de_livraison': ['livree', 'en_cours_de_livraison'],
            'livree': ['livree'],
        }

        # Vérifier si la transition souhaitée est autorisée
        allowed_transitions = valid_transitions.get(instance.statut, [])
        if new_statut not in allowed_transitions:
            raise ValidationError(
                f"Transition de statut non autorisée de '{instance.statut}' à '{new_statut}'. "
                f"Transitions autorisées : {allowed_transitions}"
            )
        if new_statut in ['prise_en_charge', 'en_cours_de_livraison', 'livree']:
            # Vérifier si le paiement de la commande a été effectué
            
            
            paiement, created = Paiement.objects.get_or_create(
                commande=instance,
                defaults={
                    'montant': instance.montant_total + instance.frais_livraison,  # Définir le montant total initial
                    'methode_paiement': '',  # Vous devrez spécifier une méthode par défaut ou la définir plus tard
                    'statut_paiement': 'en_attente',  # Définir le statut initial
                    'date_paiement': now()  # Fixer la date du paiement à l'instant actuel
                }
            )
            if paiement:
                if paiement.statut_paiement != 'payee':
                    raise ValidationError("Les transitions de statut vers 'prise en charge', 'en cours de livraison' ou 'livrée' sont uniquement autorisées si le paiement est confirmé comme 'payé'.")
            else:
                # Si aucun objet paiement n'est associé, lever une erreur
                raise ValidationError("Aucun paiement associé à cette commande. Vérification du statut du paiement impossible.")
        
        # Mettre à jour l'instance si la transition est autorisée
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if new_statut == 'en_cours_de_livraison':
            if instance.livreur:
                instance.livreur.statut = 'en_cours_de_livraison'
                instance.livreur.save()

        # Si la commande est marquée comme 'livrée', mettre à jour le statut du livreur en 'disponible'
        if new_statut == 'livree':
            if instance.livreur:
                instance.livreur.statut = 'disponible'
                instance.livreur.save()
                

        instance.save()
        return instance
    
    def perform_destroy(self, instance):
        # Restriction pour ne permettre la suppression que si la commande est 'en_cours'
        if instance.statut != 'en_cours':
            raise PermissionDenied("La suppression n'est autorisée que si la commande est 'en cours'.")
        
        super().perform_destroy(instance)

class PaiementSerializer(serializers.ModelSerializer):
    commande = CommandeSerializer(read_only=True)
    class Meta:
        model = Paiement
        fields = '__all__'




