from django.urls import path
from .views import *

urlpatterns = [
    path('company-info/', company_info, name='company_info'),
]
