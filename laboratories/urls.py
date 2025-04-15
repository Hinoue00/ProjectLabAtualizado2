# laboratories/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.laboratory_list, name='laboratory_list'),
    path('<int:pk>/', views.laboratory_detail, name='laboratory_detail'),
    path('create/', views.laboratory_create, name='laboratory_create'),
    path('<int:pk>/update/', views.laboratory_update, name='laboratory_update'),
    path('<int:pk>/delete/', views.laboratory_delete, name='laboratory_delete'),
]
