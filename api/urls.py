# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Endpoint principal do assistente
    path('assistant/', views.llama_assistant, name='llama_assistant'),
    
    # Página de teste do chatbot
    path('test-chatbot/', views.test_chatbot_page, name='test_chatbot_page'),
    
    # Página do assistente (se necessário)
    path('assistant-page/', views.assistant_page, name='assistant_page'),
    
    # Feedback do assistente
    path('assistant-feedback/', views.assistant_feedback, name='assistant_feedback'),
]