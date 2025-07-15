# inventory/ai_views.py - Views para funcionalidades de IA do inventário

from datetime import timezone
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from accounts import models
from accounts.views import is_technician
from .ai_inventory_organizer import AIInventoryOrganizer
from .models import Material, MaterialCategory
from laboratories.models import Laboratory
import json
import os
import tempfile

@login_required
@user_passes_test(is_technician)
def ai_inventory_dashboard(request):
    """Dashboard principal para funcionalidades de IA do inventário"""
    
    # Estatísticas do sistema
    total_materials = Material.objects.count()
    ai_processed = Material.objects.exclude(analyzed_data__isnull=True).count()
    categories_count = MaterialCategory.objects.count()
    labs_count = Laboratory.objects.count()
    
    # Materiais recentemente processados pela IA
    recent_ai_materials = Material.objects.exclude(
        analyzed_data__isnull=True
    ).order_by('-updated_at')[:10]
    
    # Estatísticas de automação
    automation_stats = {
        'total_materials': total_materials,
        'ai_processed': ai_processed,
        'manual_entry': total_materials - ai_processed,
        'automation_percentage': round((ai_processed / total_materials * 100) if total_materials > 0 else 0, 1),
        'categories_count': categories_count,
        'labs_count': labs_count
    }
    
    context = {
        'title': 'IA para Inventário',
        'automation_stats': automation_stats,
        'recent_ai_materials': recent_ai_materials,
    }
    
    return render(request, 'inventory/ai_dashboard.html', context)

@login_required
@user_passes_test(is_technician)
def ai_organize_inventory(request):
    """Página para organização automática de inventário com IA"""
    
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Nenhum arquivo foi selecionado.')
            return redirect('ai_organize_inventory')
        
        file = request.FILES['file']
        
        # Opções de organização
        options = {
            'merge_duplicates': request.POST.get('merge_duplicates', False),
            'auto_categorize': request.POST.get('auto_categorize', True),
            'auto_assign_labs': request.POST.get('auto_assign_labs', True),
            'generate_descriptions': request.POST.get('generate_descriptions', True),
            'create_missing_categories': request.POST.get('create_missing_categories', True),
            'create_missing_labs': request.POST.get('create_missing_labs', True)
        }
        
        try:
            # Salvar arquivo temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name
            
            # Processar com IA
            organizer = AIInventoryOrganizer()
            result = organizer.organize_inventory_from_excel(tmp_file_path, options)
            
            # Limpar arquivo temporário
            os.unlink(tmp_file_path)
            
            if result['success']:
                messages.success(request, result['message'])
                
                # Mostrar estatísticas detalhadas
                stats = result['stats']
                if stats['auto_categorized'] > 0:
                    messages.info(request, f"IA categorizou automaticamente {stats['auto_categorized']} materiais.")
                if stats['auto_assigned_lab'] > 0:
                    messages.info(request, f"IA atribuiu automaticamente {stats['auto_assigned_lab']} laboratórios.")
                if stats['descriptions_generated'] > 0:
                    messages.info(request, f"IA gerou {stats['descriptions_generated']} descrições automáticas.")
                if stats['duplicates_found'] > 0:
                    messages.warning(request, f"Encontradas e tratadas {stats['duplicates_found']} duplicatas.")
                
                return redirect('material_list')
            else:
                messages.error(request, f"Erro na organização automática: {result['error']}")
                
        except Exception as e:
            messages.error(request, f"Erro ao processar arquivo: {str(e)}")
            if 'tmp_file_path' in locals():
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
    
    context = {
        'title': 'Organização Automática com IA',
        'existing_categories': MaterialCategory.objects.all().order_by('name'),
        'existing_labs': Laboratory.objects.filter(is_active=True).order_by('name')
    }
    
    return render(request, 'inventory/ai_organize.html', context)

@login_required
@user_passes_test(is_technician)
@require_POST
@csrf_exempt
def ai_preview_organization(request):
    """API para preview da organização automática"""
    
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'Nenhum arquivo enviado'})
    
    file = request.FILES['file']
    
    try:
        # Salvar arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        # Gerar preview com IA
        organizer = AIInventoryOrganizer()
        result = organizer.get_organization_preview(tmp_file_path)
        
        # Limpar arquivo temporário
        os.unlink(tmp_file_path)
        
        return JsonResponse(result)
        
    except Exception as e:
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_technician)
def ai_categorization_assistant(request):
    """Assistente de categorização inteligente"""
    
    # Materiais sem categoria ou com categoria "Material Geral"
    uncategorized_materials = Material.objects.filter(
        category__name__in=['Material Geral', 'Diversos']
    ).order_by('name')[:50]
    
    # Sugestões de categorias baseadas em análise
    category_suggestions = []
    organizer = AIInventoryOrganizer()
    
    for material in uncategorized_materials[:20]:  # Processar apenas os primeiros 20
        try:
            suggestion = organizer._categorize_with_ai(
                material.name, 
                material.description or ''
            )
            category_suggestions.append({
                'material': material,
                'suggested_category': suggestion['category'],
                'suggested_type': suggestion['type'],
                'confidence': 0.85  # Simular confiança
            })
        except:
            continue
    
    context = {
        'title': 'Assistente de Categorização IA',
        'uncategorized_materials': uncategorized_materials,
        'category_suggestions': category_suggestions,
        'total_uncategorized': uncategorized_materials.count()
    }
    
    return render(request, 'inventory/ai_categorization.html', context)

@login_required
@user_passes_test(is_technician)
@require_POST
@csrf_exempt
def ai_apply_categorization(request):
    """Aplica categorização sugerida pela IA"""
    
    try:
        data = json.loads(request.body)
        material_id = data.get('material_id')
        suggested_category = data.get('category')
        suggested_type = data.get('type', 'consumable')
        
        material = Material.objects.get(id=material_id)
        
        # Criar categoria se não existir
        category, created = MaterialCategory.objects.get_or_create(
            name=suggested_category,
            defaults={'material_type': suggested_type}
        )
        
        # Atualizar material
        material.category = category
        material.analyzed_data = material.analyzed_data or {}
        material.analyzed_data.update({
            'ai_categorized': True,
            'categorization_date': str(timezone.now()) if 'timezone' in globals() else None,
            'confidence': 0.85
        })
        material.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Material categorizado como "{suggested_category}"',
            'category_created': created
        })
        
    except Material.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Material não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_technician)
def ai_duplicate_detector(request):
    """Detector de duplicatas usando IA"""
    
    # Buscar possíveis duplicatas
    materials = Material.objects.all().order_by('name')
    duplicates = []
    processed_names = set()
    
    organizer = AIInventoryOrganizer()
    
    for material in materials:
        normalized_name = organizer._normalize_name_for_comparison(material.name)
        
        if normalized_name in processed_names:
            continue
        
        # Buscar materiais similares
        similar_materials = []
        for other_material in materials:
            if other_material.id == material.id:
                continue
            
            other_normalized = organizer._normalize_name_for_comparison(other_material.name)
            
            # Calcular similaridade simples
            similarity = _calculate_similarity(normalized_name, other_normalized)
            
            if similarity > 0.8:  # 80% de similaridade
                similar_materials.append({
                    'material': other_material,
                    'similarity': similarity
                })
        
        if similar_materials:
            duplicates.append({
                'main_material': material,
                'similar_materials': similar_materials
            })
            processed_names.add(normalized_name)
            for sim in similar_materials:
                processed_names.add(organizer._normalize_name_for_comparison(sim['material'].name))
    
    context = {
        'title': 'Detector de Duplicatas IA',
        'duplicates': duplicates[:20],  # Limitar para performance
        'total_duplicates': len(duplicates)
    }
    
    return render(request, 'inventory/ai_duplicates.html', context)

@login_required
@user_passes_test(is_technician)
@require_POST
@csrf_exempt
def ai_merge_duplicates(request):
    """Mescla materiais duplicados"""
    
    try:
        data = json.loads(request.body)
        main_material_id = data.get('main_material_id')
        duplicate_ids = data.get('duplicate_ids', [])
        
        main_material = Material.objects.get(id=main_material_id)
        duplicate_materials = Material.objects.filter(id__in=duplicate_ids)
        
        # Somar quantidades
        total_quantity = main_material.quantity
        for duplicate in duplicate_materials:
            total_quantity += duplicate.quantity
        
        # Atualizar material principal
        main_material.quantity = total_quantity
        
        # Manter a melhor descrição
        best_description = main_material.description or ''
        for duplicate in duplicate_materials:
            if len(duplicate.description or '') > len(best_description):
                best_description = duplicate.description
        
        main_material.description = best_description
        main_material.analyzed_data = main_material.analyzed_data or {}
        main_material.analyzed_data.update({
            'merged_duplicates': True,
            'merge_date': str(timezone.now()) if 'timezone' in globals() else None,
            'merged_count': len(duplicate_ids)
        })
        main_material.save()
        
        # Deletar duplicatas
        duplicate_materials.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Materiais mesclados. Quantidade final: {total_quantity}',
            'merged_count': len(duplicate_ids)
        })
        
    except Material.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Material não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_technician)
def ai_smart_suggestions(request):
    """Sugestões inteligentes para otimização do inventário"""
    
    suggestions = []
    
    # 1. Materiais com estoque baixo que podem ser agrupados
    low_stock_materials = Material.objects.filter(is_low_stock=True)
    
    # 2. Laboratórios com materiais similares que podem ser consolidados
    labs_with_similar = {}
    
    for material in Material.objects.all()[:100]:  # Limitar para performance
        similar_in_other_labs = Material.objects.filter(
            name__icontains=material.name.split()[0]
        ).exclude(
            laboratory=material.laboratory
        ).exclude(
            id=material.id
        )
        
        if similar_in_other_labs.exists():
            if material.laboratory.name not in labs_with_similar:
                labs_with_similar[material.laboratory.name] = []
            
            labs_with_similar[material.laboratory.name].append({
                'material': material,
                'similar_in_labs': list(similar_in_other_labs)
            })
    
    # 3. Categorias que podem ser reorganizadas
    category_suggestions = []
    for category in MaterialCategory.objects.all():
        material_count = category.material_set.count()
        if material_count == 1:
            material = category.material_set.first()
            organizer = AIInventoryOrganizer()
            ai_suggestion = organizer._categorize_with_ai(
                material.name, 
                material.description or ''
            )
            if ai_suggestion['category'] != category.name:
                category_suggestions.append({
                    'current_category': category,
                    'material': material,
                    'suggested_category': ai_suggestion['category']
                })
    
    context = {
        'title': 'Sugestões Inteligentes IA',
        'low_stock_count': low_stock_materials.count(),
        'labs_with_similar': labs_with_similar,
        'category_suggestions': category_suggestions[:10],
        'total_optimizations': len(category_suggestions) + len(labs_with_similar)
    }
    
    return render(request, 'inventory/ai_suggestions.html', context)

@login_required
@user_passes_test(is_technician)
def ai_batch_processor(request):
    """Processador em lote para aplicar IA em materiais existentes"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'categorize_all':
            # Categorizar todos os materiais sem categoria
            uncategorized = Material.objects.filter(
                category__name__in=['Material Geral', 'Diversos']
            )
            
            organizer = AIInventoryOrganizer()
            categorized_count = 0
            
            for material in uncategorized:
                try:
                    suggestion = organizer._categorize_with_ai(
                        material.name, 
                        material.description or ''
                    )
                    
                    category, created = MaterialCategory.objects.get_or_create(
                        name=suggestion['category'],
                        defaults={'material_type': suggestion['type']}
                    )
                    
                    material.category = category
                    material.analyzed_data = material.analyzed_data or {}
                    material.analyzed_data.update({
                        'ai_batch_categorized': True,
                        'batch_date': str(timezone.now()) if 'timezone' in globals() else None
                    })
                    material.save()
                    categorized_count += 1
                    
                except Exception as e:
                    continue
            
            messages.success(request, f"IA categorizou automaticamente {categorized_count} materiais.")
        
        elif action == 'generate_descriptions':
            # Gerar descrições para materiais sem descrição
            no_description = Material.objects.filter(
                models.Q(description__isnull=True) | models.Q(description='')
            )
            
            organizer = AIInventoryOrganizer()
            generated_count = 0
            
            for material in no_description:
                try:
                    description = organizer._generate_description_with_ai(
                        material.name, 
                        material.category.name
                    )
                    
                    material.description = description
                    material.analyzed_data = material.analyzed_data or {}
                    material.analyzed_data.update({
                        'ai_description_generated': True,
                        'generation_date': str(timezone.now()) if 'timezone' in globals() else None
                    })
                    material.save()
                    generated_count += 1
                    
                except Exception as e:
                    continue
            
            messages.success(request, f"IA gerou automaticamente {generated_count} descrições.")
        
        return redirect('ai_batch_processor')
    
    # Estatísticas para exibição
    stats = {
        'total_materials': Material.objects.count(),
        'uncategorized': Material.objects.filter(
            category__name__in=['Material Geral', 'Diversos']
        ).count(),
        'no_description': Material.objects.filter(
            models.Q(description__isnull=True) | models.Q(description='')
        ).count(),
        'ai_processed': Material.objects.exclude(analyzed_data__isnull=True).count()
    }
    
    context = {
        'title': 'Processamento em Lote IA',
        'stats': stats
    }
    
    return render(request, 'inventory/ai_batch_processor.html', context)

# Função auxiliar para cálculo de similaridade
def _calculate_similarity(str1: str, str2: str) -> float:
    """Calcula similaridade simples entre duas strings"""
    if not str1 or not str2:
        return 0.0
    
    # Método simples de similaridade baseado em caracteres comuns
    set1 = set(str1.lower())
    set2 = set(str2.lower())
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    if union == 0:
        return 0.0
    
    return intersection / union