from django.urls import path
from .views import *

urlpatterns = [
    path('all-products/', all_products, name='all_products'),
    path('del-product/<int:id>/', del_product, name='del_product'),
    path('update-product/<int:id>/', update_product, name='update_product'),
    path('fetch_uom/', fetch_uom, name='fetch_uom'),
    ]
