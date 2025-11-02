from django.urls import path
from .views import stock

urlpatterns = [
    path('stock/', stock, name='stock'),
]
