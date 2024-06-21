import stripe
import requests
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User
from .models import Client, Commande, CommandeProduit, Produit, Livreur, Paiement
from .serializers import UserSerializer, ClientSerializer, CommandeSerializer, CommandeProduitSerializer, ProduitSerializer, LivreurSerializer, PaiementSerializer
from rest_framework import viewsets, mixins, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.decorators import action
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view


stripe.api_key = settings.STRIPE_SECRET_KEY


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [AllowAny]
    # permission_classes = [IsAuthenticated]  # Assurez-vous de configurer les permissions appropriées

    def get_queryset(self):
        # Simplifiez pour renvoyer tous les utilisateurs si l'admin est connecté, sinon l'utilisateur lui-même
        # if self.request.user.is_staff:
        #     return User.objects.all()
        return User.objects.filter(pk=self.request.user.pk)

    def get_object(self):
        # Simplification de la logique pour récupérer l'objet utilisateur
        user = self.request.user
        pk = self.kwargs.get('pk')
        if pk:
            if pk == str(user.pk) or user.is_staff:
                return super().get_object()
            else:
                raise PermissionDenied("Accès non autorisé à cet utilisateur.")
        return user

    def perform_update(self, serializer):
        # Restrict updates to self or by admins
        user = self.get_object()
        if user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas autorisé à modifier cet utilisateur.")
        serializer.save()

    def perform_destroy(self, instance):
        # Restrict deletions to self or by admins
        if instance != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("Vous n'êtes pas autorisé à supprimer cet utilisateur.")
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        # Override to handle potential PermissionDenied exceptions
        try:
            return super().update(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        # Override to handle potential PermissionDenied exceptions
        try:
            return super().destroy(request, *args, **kwargs)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({'user': UserSerializer(user, context=self.get_serializer_context()).data}, status=HTTP_201_CREATED)

# Sous-classe de UserViewSet qui ne permet que les créations
class RegisterViewSet(UserViewSet):
    permission_classes = [AllowAny]
    def get_queryset(self):
        # Cette méthode est généralement inutilisée ici mais peut être nécessaire pour certaines vérifications de permission
        return super().get_queryset()

    def list(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def retrieve(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    

class UserSelfManageViewSet(mixins.RetrieveModelMixin,  # Permet uniquement les opérations GET
                            mixins.ListModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.DestroyModelMixin,
                            viewsets.GenericViewSet):    # Utilise GenericViewSet pour plus de flexibilité
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Cette méthode retourne l'utilisateur connecté mais est configurée pour ne jamais être utilisée directement
        return User.objects.filter(pk=self.request.user.pk)

    def get_object(self):
        """
        Renvoie l'instance de l'utilisateur. Si 'pk' est 'user', renvoie l'utilisateur connecté.
        Si 'pk' est un autre identifiant, tente de récupérer l'utilisateur correspondant, si autorisé.
        """
        user = self.request.user
        pk = self.kwargs.get('pk')

        if pk == 'user':
            # Retourner l'utilisateur connecté lorsque 'pk' est 'user'
            return user
        elif pk:
            try:
                # Convertir pk en int pour éviter des erreurs de type et récupérer l'utilisateur correspondant
                pk = int(pk)
                if user.is_staff or pk == user.pk:
                    return User.objects.get(pk=pk)
                else:
                    raise PermissionDenied("Vous n'avez pas la permission de voir cet utilisateur.")
            except ValueError:
                raise ValidationError("L'identifiant doit être un nombre.")
            except User.DoesNotExist:
                raise NotFound("Aucun utilisateur avec cet identifiant.")

    # def create(self, request, *args, **kwargs):
    #     # Bloquer la création d'utilisateur via ce ViewSet
    #     return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
     
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Cette méthode renvoie l'instance de Client associée à l'utilisateur connecté.
        Si l'utilisateur est un administrateur, il peut accéder à n'importe quel client via l'ID passé dans l'URL.
        Si non, l'utilisateur ne peut accéder qu'à son propre profil client.
        """
        user = self.request.user
        pk = self.kwargs.get('pk')

        if pk == 'client':
            # Cas où 'pk' est explicitement 'client', renvoyer le client de l'utilisateur connecté
            try:
                return Client.objects.get(user=user)
            except Client.DoesNotExist:
                raise NotFound("Aucun client associé à cet utilisateur.")

        if pk:
            if user.is_staff:
                # L'administrateur peut accéder à n'importe quel client
                return super().get_object()
            else:
                # L'utilisateur essaie d'accéder à un client par ID, vérifier si c'est son ID
                try:
                    pk = int(pk)  # S'assurer que pk est un entier
                    client = Client.objects.get(pk=pk, user=user)
                    return client
                except Client.DoesNotExist:
                    raise PermissionDenied("Vous n'avez pas la permission de voir ce client.")
                except ValueError:
                    raise ValidationError("L'identifiant doit être un nombre.")
        else:
            # Aucun ID fourni, retourner le client de l'utilisateur connecté
            try:
                return Client.objects.get(user=user)
            except Client.DoesNotExist:
                raise NotFound("Aucun client associé à cet utilisateur.")

    def get_queryset(self):
        if self.request.user.is_staff:
            return Client.objects.all()
        else:
            return Client.objects.filter(user=self.request.user)
        
    def perform_update(self, serializer):
        client = serializer.instance
        # Vérifiez si l'utilisateur connecté est le même que celui lié au client, ou s'il est un membre du staff
        if self.request.user == client.user or self.request.user.is_staff:
            serializer.save()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de modifier ce client.")

    def perform_destroy(self, instance):
        # Vérifiez si l'utilisateur connecté est le même que celui lié au client, ou s'il est un membre du staff
        if self.request.user == instance.user or self.request.user.is_staff:
            instance.delete()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de supprimer ce client.")
        

def get_coordinates(address):
    """ Récupère les coordonnées géographiques d'une adresse en utilisant l'API adresse.data.gouv.fr """
    url = 'https://api-adresse.data.gouv.fr/search'
    params = {'q': address}
    response = requests.get(url, params=params)
    data = response.json()
    if data['features']:
        coordinates = data['features'][0]['geometry']['coordinates']
        return coordinates[::-1]  # Inverser pour obtenir (latitude, longitude)
    return None

def calculate_estimated_arrival_time(lat1, lon1, lat2, lon2, speed_kmph=50):
    """ Calcule l'heure d'arrivée estimée en fonction des coordonnées de départ et d'arrivée """
    from math import radians, sin, cos, sqrt, atan2

    # Rayon de la Terre
    R = 6371.0

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    travel_time_hours = distance / speed_kmph
    travel_time = timedelta(hours=travel_time_hours)

    # Obtenir l'heure actuelle et ajouter le temps de trajet pour calculer l'heure d'arrivée
    now = datetime.now()
    estimated_arrival_time = now + travel_time
    return estimated_arrival_time.strftime("%H:%M:%S")

class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')

        try:
            commande = Commande.objects.get(pk=pk)
            # Assurez-vous que les objets client et livreur ne sont pas nuls
            if not commande.client or not commande.livreur:
                raise Http404("La commande est incomplète et ne peut être traitée.")

            if user.is_staff or (commande.client and commande.client.user == user) or (commande.livreur and commande.livreur.user == user):
                return commande
            else:
                raise PermissionDenied("Vous n'avez pas la permission de voir cette commande.")
        except Commande.DoesNotExist:
            raise Http404("Aucune commande ne correspond à l'identifiant fourni.")
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Si l'utilisateur est un administrateur, retourner toutes les commandes
            return Commande.objects.all()
        else:
            # Sinon, retourner les commandes où l'utilisateur est soit le client soit le livreur
            commandes_as_client = Commande.objects.filter(client__user=user)
            commandes_as_livreur = Commande.objects.filter(livreur__user=user)
            # Utiliser 'union' pour combiner les deux QuerySets sans doublons
            return commandes_as_client.union(commandes_as_livreur)


    def perform_update(self, serializer):
        commande = serializer.instance
        user = self.request.user
        new_statut = serializer.validated_data.get('statut', commande.statut)

        # Assurer que seulement les administrateurs peuvent changer le statut en 'prise_en_charge'
        if new_statut in ['prise_en_charge'] and not user.is_staff:
            raise PermissionDenied("Vous n'avez pas la permission de changer le statut de cette commande à 'prise_en_charge'.")

        # Assurer que seulement les livreurs assignés ou les administrateurs peuvent changer le statut en 'en_cours_de_livraison' ou 'livrée'
        if new_statut in ['en_cours_de_livraison', 'livree'] and not (user.is_staff or (commande.livreur and commande.livreur.user == user)):
            raise PermissionDenied("Vous n'avez pas la permission de changer le statut de cette commande à 'en cours de livraison' ou 'livrée'.")

        if new_statut == 'en_cours_de_livraison' and commande.statut != 'en_cours_de_livraison':
            if commande.livreur and commande.client.adresse:
                # Supposons que get_coordinates et calculate_estimated_arrival_time sont des fonctions définies pour interagir avec une API ou calculer les coordonnées/temps
                origin_coords = get_coordinates("14 Avenue de l'Europe 77144 Montévrain")
                destination_coords = get_coordinates(commande.client.adresse)
                if origin_coords and destination_coords:
                    arrival_time = calculate_estimated_arrival_time(*origin_coords, *destination_coords)
                    serializer.validated_data['temps_estime_livraison'] = arrival_time
                else:
                    raise ValidationError("Impossible de récupérer les coordonnées pour le calcul de l'heure d'arrivée.")

        if user.is_staff or commande.client.user == user or (commande.livreur and commande.livreur.user == user):
            serializer.save()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de modifier cette commande.")

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_staff or instance.client.user == user:
            instance.delete()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de supprimer cette commande.")

class CommandeProduitViewSet(viewsets.ModelViewSet):
    queryset = CommandeProduit.objects.all()
    serializer_class = CommandeProduitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return CommandeProduit.objects.all()
        else:
            return CommandeProduit.objects.filter(commande__client__user=self.request.user)
        
    def perform_create(self, serializer):
        # Ici, vous pouvez ajouter une logique pour vérifier si l'utilisateur a le droit de créer une entrée
        commande = serializer.validated_data['commande']
        if self.request.user == commande.client.user or self.request.user.is_staff:
            serializer.save()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de créer cette entrée.")

    def perform_update(self, serializer):
        commande = serializer.instance.commande
        if self.request.user == commande.client.user or self.request.user.is_staff:
            serializer.save()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de modifier cette entrée.")

    def perform_destroy(self, instance):
        commande = instance.commande
        if self.request.user == commande.client.user or self.request.user.is_staff:
            instance.delete()
        else:
            raise PermissionDenied("Vous n'avez pas la permission de supprimer cette entrée.")

class ProduitViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    Un viewset qui fournit uniquement les opérations 'list' et 'retrieve'.
    """
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class LivreurViewSet(mixins.RetrieveModelMixin,  # Permet la récupération d'un livreur spécifique par son ID
                     mixins.ListModelMixin,      # Permet de lister tous les livreurs
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):   # Base pour la construction de viewsets sans méthodes CRUD par défaut
    """
    Un viewset qui fournit uniquement les opérations 'retrieve' et 'list' pour les livreurs.
    """
    queryset = Livreur.objects.all()
    serializer_class = LivreurSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Permet aux administrateurs de voir tous les livreurs, mais les livreurs peuvent seulement se voir eux-mêmes
        if self.request.user.is_staff:
            return Livreur.objects.all()
        else:
            return Livreur.objects.filter(user=self.request.user)
        
    def get_object(self):
        """
        Cette méthode renvoie l'instance de Livreur associée à l'utilisateur connecté.
        Si l'utilisateur est un administrateur, il peut accéder à n'importe quel livreur via l'ID passé dans l'URL.
        Si non, l'utilisateur ne peut accéder qu'à son propre profil de livreur.
        """
        user = self.request.user
        pk = self.kwargs.get('pk')

        if pk == 'livreur':
            # Cas où 'pk' est explicitement 'livreur', renvoyer le livreur de l'utilisateur connecté
            try:
                return Livreur.objects.get(user=user)
            except Livreur.DoesNotExist:
                raise NotFound("Aucun livreur associé à cet utilisateur.")

        if pk:
            if user.is_staff:
                # L'administrateur peut accéder à n'importe quel livreur
                return super().get_object()
            else:
                # L'utilisateur essaie d'accéder à un livreur par ID, vérifier si c'est son ID
                try:
                    pk = int(pk)  # S'assurer que pk est un entier
                    livreur = Livreur.objects.get(pk=pk, user=user)
                    return livreur
                except Livreur.DoesNotExist:
                    raise PermissionDenied("Vous n'avez pas la permission de voir cet utilisateur.")
                except ValueError:
                    raise ValidationError("L'identifiant doit être un nombre.")
        else:
            # Aucun ID fourni, retourner le livreur de l'utilisateur connecté
            try:
                return Livreur.objects.get(user=user)
            except Livreur.DoesNotExist:
                raise NotFound("Aucun livreur associé à cet utilisateur.")
        
    def perform_update(self, serializer):
        user = self.request.user
        pk = self.kwargs.get('pk')
        
        # Récupération du livreur, soit par l'utilisateur connecté soit par pk
        if pk == 'livreur':
            try:
                livreur = Livreur.objects.get(user=user)
            except Livreur.DoesNotExist:
                raise NotFound("Aucun livreur associé à cet utilisateur.")
        else:
            if pk and user.is_staff:
                livreur = super().get_object()
            elif pk:
                try:
                    pk = int(pk)  # S'assurer que pk est un entier
                    livreur = Livreur.objects.get(pk=pk, user=user)
                except ValueError:
                    raise ValidationError("L'identifiant doit être un nombre.")
                except Livreur.DoesNotExist:
                    raise PermissionDenied("Vous n'avez pas la permission de voir ce livreur.")

        # Vérification du statut actuel du livreur avant autorisation de mise à jour
        if livreur.statut == 'en_cours_de_livraison':
            raise ValidationError("Le livreur est en cours de livraison et ne peut pas modifier son statut.")

        # Vérifie si l'utilisateur est l'administrateur ou le livreur associé
        if user != livreur.user and not user.is_staff:
            raise PermissionDenied("Vous n'avez pas la permission de modifier ce livreur.")
        
        serializer.save()

        

class PaiementViewSet(mixins.RetrieveModelMixin,  # Permet la récupération d'un paiement spécifique par son ID
                      mixins.ListModelMixin,      # Permet de lister tous les paiements
                      viewsets.GenericViewSet):   # Base pour la construction de viewsets sans méthodes CRUD par défaut
    """
    Un viewset qui fournit uniquement les opérations 'retrieve' et 'list' pour les paiements.
    """
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Permet aux administrateurs de voir tous les paiements, mais les utilisateurs réguliers ne voient que leurs paiements
        if self.request.user.is_staff:
            return Paiement.objects.all()
        else:
            return Paiement.objects.filter(commande__client__user=self.request.user)
        
        
class CommandePaiementViewSet(CommandeViewSet, viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer
    
    def list(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request, *args, **kwargs):
        # Désactiver la création standard
        return Response({'error': 'Action non autorisée.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        # Désactiver la mise à jour standard
        return Response({'error': 'Action non autorisée.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'])
    def create_payment_intent(self, request, pk=None):
        commande = self.get_object()
        user = request.user
        try:
            # Vérifier si l'utilisateur a le droit de créer un PaymentIntent
            if not (user == commande.client.user or user.is_staff):
                return Response({'error': "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

            # Vérifier si un paiement existe déjà et est déjà payé
            paiement, created = Paiement.objects.get_or_create(
                commande=commande,
                defaults={'montant': commande.montant_total + commande.frais_livraison}
            )
            if not created and paiement.statut_paiement == 'payee':
                return Response({'error': "Paiement déjà effectué."}, status=status.HTTP_400_BAD_REQUEST)

            # Calcul du montant à charger (centimes)
            amount = int((commande.montant_total + commande.frais_livraison) * 100)

            # Création d'un PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='eur',
                metadata={'commande_id': commande.id}
            )

            # Mise à jour ou création du paiement
            paiement.payment_token = intent.id
            paiement.methode_paiement = 'stripe'
            paiement.statut_paiement = 'en_attente'
            paiement.save()

            return Response({'client_secret': intent['client_secret']}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
    @action(detail=True, methods=['post'])
    def verify_payment(self, request, pk=None):
        commande = self.get_object()
        user = request.user
        try:
            if not (user == commande.client.user or user.is_staff):
                return Response({'error': "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

            paiement = Paiement.objects.get(commande=commande)

            if paiement.statut_paiement == 'payee':
                return Response({'error': 'Paiement déjà vérifié.'}, status=status.HTTP_400_BAD_REQUEST)

            if not paiement.payment_token:
                return Response({'error': 'Aucun token de paiement associé à cette commande.'}, status=status.HTTP_404_NOT_FOUND)

            # Utilisez Stripe pour vérifier le statut du PaymentIntent
            intent = stripe.PaymentIntent.retrieve(paiement.payment_token)

            # Mise à jour du statut de paiement selon le statut Stripe
            if intent.status == 'succeeded':
                paiement.statut_paiement = 'payee'
                commande.statut = 'prise_en_charge'
                paiement.save()
                commande.save()
                return Response({'status': 'success', 'message': 'Paiement vérifié et commande mise à jour.'})
            else:
                return Response({'status': 'failed', 'message': 'Paiement non réussi.'})
        except Paiement.DoesNotExist:
            return Response({'error': 'Paiement non trouvé pour cette commande.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        

@api_view(['POST'])
def create_payment_intent(request):
    try:
        data = request.data
        amount = int(data['amount'] * 100)  # Convertir en centimes
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='eur',
            metadata={'integration_check': 'accept_a_payment'}
        )
        return JsonResponse({'client_secret': intent['client_secret']})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@api_view(['POST'])
def verify_payment(request):
    try:
        payment_intent_id = request.data.get('paymentIntentId')
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if payment_intent.status == 'succeeded':
            # Logique pour traiter la commande comme payée
            return JsonResponse({'status': 'success', 'message': 'Paiement vérifié'})
        else:
            return JsonResponse({'status': 'failed', 'message': 'Paiement non réussi'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)