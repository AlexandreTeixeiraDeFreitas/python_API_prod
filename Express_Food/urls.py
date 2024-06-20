"""
URL configuration for Express_Food project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as auth_views
from backoffice import views
from backoffice.views import create_payment_intent

router = DefaultRouter()

router.register(r'inscription', views.RegisterViewSet)
router.register(r'users', views.UserSelfManageViewSet, basename='get-user')
router.register(r'clients', views.ClientViewSet)
router.register(r'commandes', views.CommandeViewSet)
router.register(r'produits', views.ProduitViewSet)
router.register(r'livreurs', views.LivreurViewSet)
router.register(r'commande_produits', views.CommandeProduitViewSet)
router.register(r'paiements', views.PaiementViewSet)
router.register(r'createpaiement', views.CommandePaiementViewSet, basename='createpaiement')

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include('backoffice.urls')),  # Inclure les URL de votre application
    #path('create-payment-intent/', create_payment_intent, name='create-payment-intent'),  # Ajoutez cette ligne
    path('connexion/', auth_views.obtain_auth_token),
    path('', include(router.urls)),
    # path('back/', views.back, name='back'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)