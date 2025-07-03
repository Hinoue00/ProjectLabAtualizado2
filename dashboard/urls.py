# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('technician/', views.technician_dashboard, name='technician_dashboard'),
    path('professor/', views.professor_dashboard, name='professor_dashboard'),
    path('chart-data/', views.chart_data, name='chart_data'),
        
    # APIs para o professor
    path('api/professor-stats/', views.professor_stats_api, name='professor_stats_api'),
    path('api/upcoming-classes/', views.upcoming_classes_api, name='upcoming_classes_api'),
    path('api/laboratory-availability/', views.laboratory_availability_api, name='laboratory_availability_api'),
    path('api/laboratory/<int:lab_id>/availability/', views.lab_specific_availability_api, name='lab_specific_availability_api'),
    path('api/schedule-conflict-check/', views.schedule_conflict_check_api, name='schedule_conflict_check_api'),
    path('api/notifications/check/', views.notifications_check_api, name='notifications_check_api'),
]