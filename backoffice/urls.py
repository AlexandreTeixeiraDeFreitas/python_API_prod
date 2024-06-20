from django.urls import path
from .views import create_payment_intent

urlpatterns = [
    path('create-payment-intent/', create_payment_intent, name='create-payment-intent'),
]
