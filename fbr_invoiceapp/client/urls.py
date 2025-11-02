from django.urls import path
from .views import *

urlpatterns = [
    path('clients/', client_list, name='client_list'),
    # path('clients/<int:pk>/', client_detail, name='client_detail'),
    path('clients/create/', client_create, name='client_create'),
    path("check-registration-type/", check_registration_type, name="check_registration_type"),
    path('clients/<int:client_id>/update/', client_edit, name='client_edit'),
    path('clients/delete/<int:client_id>/', client_delete, name='client_delete'),
    # path('clients/<int:pk>/delete/', client_delete, name='client_delete'),
]