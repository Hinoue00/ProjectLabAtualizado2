# inventory/intelligent_views.py - Views para Análise Inteligente (Corrigida)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from accounts.views import is_technician
from .models import Material, MaterialCategory
from .services import DoclingService
import json
from typing import Dict, Any

# Inicializar serviço inteligente
docling_service = DoclingService()

@login_required
@user_passes_test(is_technician)
def analyze_materials_batch(request):
    """
    Página principal para análise em lote de materiais
    """
    # Estatísticas gerais
    total_materials = Material.objects.count()
    analyzed_materials = Material.objects.exclude(analyzed_data__isnull=True).count()
    unanalyzed_materials = total_materials - analyzed_materials
    
    # Materiais com baixa qualidade de descrição
    poor_descriptions = Material.objects.filter(
        Q(description__isnull=True) | 
        Q(description__exact='') | 
        Q(description__regex=r'^.{1,10}$')  # Menos de 10 caracteres
    ).count()
    
    # Insights do inventário
    try:
        inventory_insights = docling_service.generate_inventory_insights()
    except Exception as e:
        inventory_insights = {'error': str(e)}
        messages.warning(request, f'Erro ao gerar insights: {str(e)}')
    
    # Processar análise em lote se solicitado
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'analyze_unanalyzed':
            return _process_unanalyzed_materials(request)
        elif action == 'recategorize_all':
            return _recategorize_all_materials(request)
        elif action == 'improve_descriptions':
            return _improve_descriptions(request)
    
    context = {
        'total_materials': total_materials,
        'analyzed_materials': analyzed_materials,
        'unanalyzed_materials': unanalyzed_materials,
        'poor_descriptions': poor_descriptions,
        'analysis_percentage': (analyzed_materials / total_materials * 100) if total_materials > 0 else 0,
        'insights': inventory_insights,
        'docling_enabled': docling_service.enabled,
    }
    
    return render(request, 'inventory/analyze_batch.html', context)

@login_required
@user_passes_test(is_technician)
def material_trends(request):
    """
    Página de tendências e análises avançadas
    """
    # Parâmetros de filtro
    category_filter = request.GET.get('category', 'all')
    time_range = request.GET.get('range', '30')  # dias
    
    # Análise de categorização
    categorization_data = []
    for category in MaterialCategory.objects.all():
        materials = category.material_set.all()
        avg_confidence = 0
        
        if materials:
            confidences = []
            for material in materials:
                analysis = docling_service.categorize_material(
                    material.description, material.name
                )
                confidences.append(analysis['confidence'])
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        categorization_data.append({
            'category': category,
            'count': materials.count(),
            'avg_confidence': avg_confidence
        })
    
    # Materiais com categorização incerta
    uncertain_materials = []
    materials = Material.objects.select_related('category')[:50]  # Limitar para performance
    
    for material in materials:
        analysis = docling_service.categorize_material(
            material.description, material.name
        )
        
        if analysis['confidence'] < 0.6:
            uncertain_materials.append({
                'material': material,
                'analysis': analysis
            })
    
    # Top palavras-chave
    all_keywords = []
    for material in Material.objects.exclude(analyzed_data__isnull=True)[:100]:
        if material.analyzed_data and 'keywords' in material.analyzed_data:
            all_keywords.extend(material.analyzed_data['keywords'])
    
    from collections import Counter
    top_keywords = Counter(all_keywords).most_common(20)
    
    context = {
        'categorization_data': categorization_data,
        'uncertain_materials': uncertain_materials[:10],
        'top_keywords': top_keywords,
        'category_filter': category_filter,
        'time_range': time_range,
    }
    
    return render(request, 'inventory/material_trends.html', context)

@login_required
@user_passes_test(is_technician)
def material_insights(request, material_id):
    """
    Insights detalhados para um material específico
    """
    material = get_object_or_404(Material, id=material_id)
    
    # Análise completa do material
    analysis = docling_service.analyze_text(f"{material.name} {material.description}")
    categorization = docling_service.categorize_material(material.description, material.name)
    suggestions = docling_service.suggest_material_improvements(material_id)
    similar_materials = docling_service.find_similar_materials(material_id)
    
    context = {
        'material': material,
        'analysis': analysis,
        'categorization': categorization,
        'suggestions': suggestions,
        'similar_materials': similar_materials,
    }
    
    return render(request, 'inventory/material_insights.html', context)

@csrf_exempt
@require_POST
def analyze_description_api(request):
    """
    API para análise em tempo real de descrições
    """
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
        name = data.get('name', '')
        
        if not description:
            return JsonResponse({'error': 'Descrição não fornecida'}, status=400)
        
        # Análise completa
        analysis = docling_service.analyze_text(description)
        categorization = docling_service.categorize_material(description, name)
        
        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'categorization': categorization,
            'suggestions': {
                'category': categorization['category'],
                'confidence': categorization['confidence'],
                'explanation': categorization['explanation'],
                'suggested_lab': categorization.get('suggested_lab')
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def suggest_improvements_api(request):
    """
    API para sugerir melhorias em um material
    """
    try:
        data = json.loads(request.body)
        material_id = data.get('material_id')
        
        if not material_id:
            return JsonResponse({'error': 'ID do material não fornecido'}, status=400)
        
        suggestions = docling_service.suggest_material_improvements(material_id)
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def find_similar_api(request):
    """
    API para encontrar materiais similares
    """
    try:
        data = json.loads(request.body)
        material_id = data.get('material_id')
        limit = data.get('limit', 5)
        
        if not material_id:
            return JsonResponse({'error': 'ID do material não fornecido'}, status=400)
        
        similar_materials = docling_service.find_similar_materials(material_id, limit)
        
        # Serializar dados para JSON
        similar_data = []
        for item in similar_materials:
            similar_data.append({
                'id': item['material'].id,
                'name': item['material'].name,
                'description': item['material'].description,
                'category': item['material'].category.name,
                'similarity': item['similarity'],
                'common_keywords': item['common_keywords']
            })
        
        return JsonResponse({
            'success': True,
            'similar_materials': similar_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(is_technician)
def inventory_dashboard(request):
    """
    Dashboard avançado do inventário com insights de IA
    """
    # Estatísticas gerais
    stats = {
        'total_materials': Material.objects.count(),
        'categories': MaterialCategory.objects.count(),
        'low_stock_count': Material.objects.filter(
            quantity__lte=F('minimum_stock')
        ).count(),
    }
    
    # Insights avançados
    try:
        insights = docling_service.generate_inventory_insights()
        
        # Adicionar recomendações
        recommendations = []
        
        if insights.get('anomalies'):
            recommendations.append({
                'type': 'warning',
                'title': 'Categorias Incorretas Detectadas',
                'message': f"{len(insights['anomalies'])} materiais podem estar na categoria errada",
                'action_url': '/inventory/trends/#anomalies'
            })
        
        if insights['description_quality']['low_quality_count'] > 0:
            recommendations.append({
                'type': 'info',
                'title': 'Melhorar Descrições',
                'message': f"{insights['description_quality']['low_quality_count']} materiais precisam de descrições melhores",
                'action_url': '/inventory/analyze-batch/'
            })
        
        insights['recommendations'] = recommendations
        
    except Exception as e:
        insights = {'error': str(e)}
        messages.error(request, f'Erro ao gerar insights: {str(e)}')
    
    context = {
        'stats': stats,
        'insights': insights,
    }
    
    return render(request, 'inventory/dashboard.html', context)

# Funções auxiliares para processamento em lote

def _process_unanalyzed_materials(request):
    """Processar materiais não analisados"""
    try:
        batch_size = int(request.POST.get('batch_size', 50))
        unanalyzed = Material.objects.filter(analyzed_data__isnull=True)[:batch_size]
        
        processed_count = 0
        for material in unanalyzed:
            try:
                # Analisar material
                analysis = docling_service.analyze_text(
                    f"{material.name} {material.description}"
                )
                
                # Salvar análise
                material.analyzed_data = analysis
                material.save()
                processed_count += 1
                
            except Exception as e:
                messages.warning(request, f'Erro ao analisar {material.name}: {str(e)}')
        
        messages.success(request, f'{processed_count} materiais analisados com sucesso!')
        
    except Exception as e:
        messages.error(request, f'Erro no processamento: {str(e)}')
    
    return redirect('analyze_materials_batch')

def _recategorize_all_materials(request):
    """Recategorizar todos os materiais"""
    try:
        materials = Material.objects.all()
        recategorized_count = 0
        
        for material in materials:
            try:
                # Análise de categoria
                categorization = docling_service.categorize_material(
                    material.description, material.name
                )
                
                # Se confiança for alta e categoria diferente, sugerir mudança
                if (categorization['confidence'] > 0.7 and 
                    categorization['category'] != material.category.material_type):
                    
                    # Buscar ou criar nova categoria
                    new_category = MaterialCategory.objects.filter(
                        material_type=categorization['category']
                    ).first()
                    
                    if new_category:
                        material.category = new_category
                        material.save()
                        recategorized_count += 1
                
            except Exception as e:
                continue
        
        messages.success(request, f'{recategorized_count} materiais recategorizados!')
        
    except Exception as e:
        messages.error(request, f'Erro na recategorização: {str(e)}')
    
    return redirect('analyze_materials_batch')

def _improve_descriptions(request):
    """Melhorar descrições pobres"""
    try:
        poor_materials = Material.objects.filter(
            Q(description__isnull=True) | 
            Q(description__exact='') | 
            Q(description__regex=r'^.{1,10}$')
        )[:20]  # Limitar para não sobrecarregar
        
        improved_count = 0
        
        for material in poor_materials:
            try:
                # Gerar descrição baseada no nome e categoria
                category_context = material.category.name
                suggested_desc = f"{material.name} - {category_context} para uso em laboratório"
                
                if len(material.description or '') < 20:
                    material.description = suggested_desc
                    material.save()
                    improved_count += 1
                
            except Exception as e:
                continue
        
        messages.success(request, f'{improved_count} descrições melhoradas!')
        
    except Exception as e:
        messages.error(request, f'Erro na melhoria de descrições: {str(e)}')
    
    return redirect('analyze_materials_batch')