# scheduling/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('calendar/', views.schedule_calendar, name='schedule_calendar'),
    path('request/', views.create_schedule_request, name='create_schedule_request'),
    path('request/<int:pk>/', views.schedule_request_detail, name='schedule_request_detail'),
    path('request/<int:pk>/edit/', views.edit_schedule_request, name='edit_schedule_request'),
    path('request/<int:pk>/cancel/', views.cancel_schedule_request, name='cancel_schedule_request'),
    path('pending/', views.pending_requests_list, name='pending_requests'),
    path('requests/<int:pk>/approve/', views.approve_schedule_request, name='approve_schedule_request'),
    path('requests/<int:pk>/reject/', views.reject_schedule_request, name='reject_schedule_request'),
    path('drafts/', views.list_draft_schedule_requests, name='list_draft_schedule_requests'),
    path('drafts/view/', views.view_draft_schedule_requests, name='view_draft_schedule_requests'),
    path('drafts/<int:draft_id>/confirm/', views.confirm_draft_schedule_request, name='confirm_draft_schedule_request'),
    path('drafts/<int:draft_id>/delete/', views.delete_draft_schedule_request, name='delete_draft_schedule_request'),
    path('drafts/<int:draft_id>/edit/', views.edit_draft_schedule_request, name='edit_draft_schedule_request'),
    path('api/calendar-data/', views.calendar_data_api, name='calendar_data_api'),
    path('api/calendar-data/', views.calendar_data_api, name='calendar_data_api'),
    path('api/schedule-detail/<int:schedule_id>/', views.schedule_detail_api, name='schedule_detail_api'),
    path('api/laboratory-materials/<int:laboratory_id>/', views.get_laboratory_materials, name='get_laboratory_materials'),
    path('api/request/<int:pk>/comments/', views.get_request_comments, name='get_request_comments'),
    path('api/request/<int:pk>/add-comment/', views.add_comment_to_request, name='add_comment_to_request'),
    path('my-requests/', views.my_schedule_requests, name='my_schedule_requests'),
    path('api/mark-notifications-read/', views.mark_all_notifications_read, name='mark_notifications_read'),
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('technician-edit/<int:pk>/', views.technician_edit_schedule, name='technician_edit_schedule'),
    path('create-exception/', views.create_exception_schedule, name='create_exception_schedule'),
    path('api/storage-materials/', views.storage_materials_api, name='storage_materials_api'),
]
