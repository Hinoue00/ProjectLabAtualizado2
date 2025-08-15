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
    
    # URLs para reset de senha
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('password-reset/<str:token>/', views.password_reset_view, name='password_reset'),
    path('password-reset-requests/', views.password_reset_requests_view, name='password_reset_requests'),
    path('approve-password-reset/<int:request_id>/', views.approve_password_reset, name='approve_password_reset'),
    path('reject-password-reset/<int:request_id>/', views.reject_password_reset, name='reject_password_reset'),
]