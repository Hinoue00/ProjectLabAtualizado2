# api/urls.py
from django.urls import path
from . import views
from . import views_deploy

urlpatterns = [
    # Endpoint principal do assistente
    path('assistant/', views.llama_assistant, name='llama_assistant'),
    
    # Página de teste do chatbot
    path('test-chatbot/', views.test_chatbot_page, name='test_chatbot_page'),
    
    # Página do assistente (se necessário)
    path('assistant-page/', views.assistant_page, name='assistant_page'),
    
    # Feedback do assistente
    path('assistant-feedback/', views.assistant_feedback, name='assistant_feedback'),
    
    # Deploy webhook endpoints
    path('deploy/', views_deploy.deploy_webhook, name='deploy_webhook'),
    path('deploy/status/', views_deploy.deploy_status, name='deploy_status'),
]