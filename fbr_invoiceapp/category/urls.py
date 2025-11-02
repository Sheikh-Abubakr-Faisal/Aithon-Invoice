from django.urls import path
from .views import *

urlpatterns = [
    path('category/', category, name='category'),
    path('del-category/<int:id>/', del_category, name='del_category'),
    path('update-category/<int:id>/', update_category, name='update_category'),
    ]