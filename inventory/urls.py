# inventory/urls.py - URLs com placeholders para não quebrar o template
from django.urls import path
from . import views

# Views placeholder para não quebrar o template
def placeholder_view(request):
    from django.shortcuts import render
    from django.contrib import messages
    messages.info(request, 'Esta funcionalidade está em desenvolvimento.')
    return render(request, 'inventory/placeholder.html', {
        'title': 'Funcionalidade em Desenvolvimento',
        'message': 'Esta funcionalidade será implementada em breve.'
    })

urlpatterns = [
    # URLs principais (views que existem confirmadas)
    path('', views.material_list, name='material_list'),
    path('materials/', views.material_list, name='material_list_alt'),
    
    # CRUD de materiais (views confirmadas)
    path('materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/update/', views.material_update, name='material_update'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    
    # CRUD de categorias (views confirmadas)
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    
    # Importação e exportação (views confirmadas)
    path('import/', views.import_materials, name='import_materials'),
    path('export/', views.export_materials, name='export_materials'),
    
    # Placeholders temporários para não quebrar o template
    path('analyze-batch/', placeholder_view, name='analyze_materials_batch'),
    path('trends/', placeholder_view, name='material_trends'),
    path('download-template/', placeholder_view, name='download_template'),
    
    # APIs placeholder
    path('api/analyze-description/', placeholder_view, name='analyze_material_description'),
    path('api/suggest-material/', placeholder_view, name='suggest_material_details'),
]