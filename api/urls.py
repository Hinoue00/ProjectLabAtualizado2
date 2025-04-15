# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # path('assistant/', views.claude_assistant, name='claude_assistant'),
    path('assistant/', views.llama_assistant, name='llama_assistant'),
    # path('assistant-page/', views.assistant_page, name='assistant_page'),
    
]