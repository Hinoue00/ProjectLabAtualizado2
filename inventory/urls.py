# inventory/urls.py - URLs Limpas e Organizadas
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from . import views
from . import ai_views
import json

# View placeholder para funcionalidades não implementadas
def placeholder_view(request):
    messages.info(request, 'Esta funcionalidade está em desenvolvimento.')
    context = {
        'title': 'Funcionalidade em Desenvolvimento',
        'message': 'Esta funcionalidade será implementada em breve.'
    }
    return render(request, 'inventory/placeholder.html', context)

# API placeholder para análise de descrição
@csrf_exempt
@require_POST
def analyze_material_description_placeholder(request):
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
        
        return JsonResponse({
            'success': True,
            'suggested_category': 'consumable',
            'suggested_category_display': 'Consumível',
            'keywords': description.split()[:5],
            'confidence': 0.5
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# API placeholder para sugestões de material
@csrf_exempt
@require_POST
def suggest_material_details_placeholder(request):
    try:
        suggestions = [
            {'name': 'Papel A4', 'description': 'Papel para impressão'},
            {'name': 'Caneta', 'description': 'Caneta para escrita'},
            {'name': 'Microscópio', 'description': 'Equipamento de laboratório'}
        ]
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions[:3]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)



urlpatterns = [
    # URLs principais (CRUD básico) - FUNCIONAM PERFEITAMENTE
    path('', views.material_list, name='material_list'),
    path('materials/', views.material_list, name='material_list_alt'),
    path('materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/update/', views.material_update, name='material_update'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    
    # URLs de categorias - FUNCIONAM PERFEITAMENTE
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    
    # URLs de importação/exportação - FUNCIONAM PERFEITAMENTE
    path('import/', views.import_materials, name='import_materials'),
    path('export/', views.export_materials, name='export_materials'),
    
    # ✅ FUNCIONALIDADE REAL: Download de Template Excel
    path('download-template/', views.download_template_excel, name='download_template_excel'),
    
    # APIs básicas (placeholders funcionais)
    path('api/analyze-description/', analyze_material_description_placeholder, name='analyze_material_description'),
    path('api/suggest-material/', suggest_material_details_placeholder, name='suggest_material_details'),
    
    # Funcionalidades de IA - EM DESENVOLVIMENTO
    path('analyze-batch/', placeholder_view, name='analyze_materials_batch'),
    path('trends/', placeholder_view, name='material_trends'),
    path('api/suggest-improvements/', placeholder_view, name='suggest_improvements_api'),
    path('api/find-similar/', placeholder_view, name='find_similar_api'),

    # URLs para funcionalidades de IA
    path('ai/', ai_views.ai_inventory_dashboard, name='ai_inventory_dashboard'),
    path('ai/organize/', ai_views.ai_organize_inventory, name='ai_organize_inventory'),
    path('ai/categorization/', ai_views.ai_categorization_assistant, name='ai_categorization_assistant'),
    path('ai/duplicates/', ai_views.ai_duplicate_detector, name='ai_duplicate_detector'),
    path('ai/suggestions/', ai_views.ai_smart_suggestions, name='ai_smart_suggestions'),
    path('ai/batch/', ai_views.ai_batch_processor, name='ai_batch_processor'),

    # APIs para IA
    path('ai/api/preview/', ai_views.ai_preview_organization, name='ai_preview_organization'),
    path('ai/api/categorize/', ai_views.ai_apply_categorization, name='ai_apply_categorization'),
    path('ai/api/merge/', ai_views.ai_merge_duplicates, name='ai_merge_duplicates'),
]

