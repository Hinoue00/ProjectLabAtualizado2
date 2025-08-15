# reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('generate/', views.generate_report, name='generate_report'),
    path('scheduling/<int:report_id>/<str:format>/', views.scheduling_report, name='scheduling_report'),
    path('inventory/<int:report_id>/<str:format>/', views.inventory_report, name='inventory_report'),
    path('user-activity/<int:report_id>/<str:format>/', views.user_activity_report, name='user_activity_report'),
]