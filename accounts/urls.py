# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_register_view, name='login'),
    path('register/', views.login_register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('pending-user/', views.pending_user, name='pending_user'),
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('check-approval-status/', views.check_approval_status, name='check_approval_status'),
    path('test-whatsapp/', views.test_whatsapp_message, name='test_whatsapp'),
]