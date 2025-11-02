from django.contrib import admin
from django.urls import path, include
from base.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('sign-in/', sign_in, name='sign_in'),
    path('logout/', user_logout, name='user_logout'),
    path('', include('category.urls')),
    path('', include('company.urls')),
    path('', include('dashboard.urls')),
    path('', include('product.urls')),
    path('', include('purchase_inv.urls')),
    path('', include('sale_inv.urls')),
    path('', include('stock.urls')),
    path('', include('client.urls')),
    path('', include('contact.urls')),
]
