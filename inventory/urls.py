# inventory/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('materials/', views.material_list, name='material_list'),
    path('materials/create/', views.material_create, name='material_create'),
    path('materials/<int:pk>/update/', views.material_update, name='material_update'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    path('import/', views.import_materials, name='import_materials'),
    path('export/', views.export_materials, name='export_materials'),
    path('api/analyze-description/', views.analyze_material_description, name='analyze_material_description'),
    path('materials/<int:pk>/', views.material_detail, name='material_detail'),
    path('analyze-batch/', views.analyze_materials_batch, name='analyze_materials_batch'),
    path('api/suggest-material/', views.suggest_material_details, name='suggest_material_details'),
    path('trends/', views.material_trends, name='material_trends'),
    path('download-template/', views.download_template, name='download_template'),
]