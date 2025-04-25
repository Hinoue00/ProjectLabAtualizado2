# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('technician/', views.technician_dashboard, name='technician_dashboard'),
    path('professor/', views.professor_dashboard, name='professor_dashboard'),
    path('chart-data/', views.chart_data, name='chart_data'),
]