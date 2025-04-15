# inventory/views.py
from itertools import count
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from accounts.views import is_technician
from .models import Material, MaterialCategory
from .forms import MaterialForm, MaterialCategoryForm, ImportMaterialsForm
from laboratories.models import Laboratory
import pandas as pd
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
import csv
import io
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .services import DoclingService
from django.conf import settings

docling_service = DoclingService() if getattr(settings, 'DOCLING_ENABLED', False) else None


@login_required
@user_passes_test(is_technician)
def material_list(request):
    # Get search parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    laboratory_filter = request.GET.get('laboratory', '')
    stock_status = request.GET.get('stock_status', '')
    
    # Filter materials
    materials = Material.objects.select_related('category', 'laboratory').all()
    
    if search_query:
        if docling_service and len(search_query) > 3:
            # Pesquisa semântica melhorada
            analyzed_query = docling_service.analyze_text(search_query)
            keywords = analyzed_query.get('keywords', [])
            
            # Criar filtros OR para cada palavra-chave
            query_filter = models.Q()
            for keyword in keywords:
                query_filter |= models.Q(name__icontains=keyword) 
                query_filter |= models.Q(description__icontains=keyword)
                
            # Filtrar por análise de dados também se disponível
            materials = materials.filter(
                query_filter | 
                models.Q(analyzed_data__keywords__contains=keywords)
            ).distinct()
        else:
            # Pesquisa tradicional
            materials = materials.filter(
                models.Q(name__icontains=search_query) | 
                models.Q(description__icontains=search_query)
            )
    
    if category_filter:
        materials = materials.filter(category__id=category_filter)
    
    if laboratory_filter:
        materials = materials.filter(laboratory__id=laboratory_filter)
    
    if stock_status == 'low':
        materials = materials.filter(quantity__lte=models.F('minimum_stock'))
    
    # Get categories and laboratories for filter dropdowns
    categories = MaterialCategory.objects.all()
    laboratories = Laboratory.objects.all()
    
    context = {
        'materials': materials,
        'categories': categories,
        'laboratories': laboratories,
        'search_query': search_query,
        'category_filter': category_filter,
        'laboratory_filter': laboratory_filter,
        'stock_status': stock_status,
    }
    
    return render(request, 'material_list.html', context)

@login_required
@user_passes_test(is_technician)
def material_create(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Material added successfully.')
            return redirect('material_list')
    else:
        form = MaterialForm()
    
    return render(request, 'material_form.html', {'form': form, 'title': 'Add Material'})

@login_required
@user_passes_test(is_technician)
def material_update(request, pk):
    material = get_object_or_404(Material, pk=pk)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, 'Material updated successfully.')
            return redirect('material_list')
    else:
        form = MaterialForm(instance=material)
    
    return render(request, 'material_form.html', {
        'form': form, 
        'title': 'Update Material',
        'material': material
    })

@login_required
@user_passes_test(is_technician)
def material_delete(request, pk):
    material = get_object_or_404(Material, pk=pk)
    
    if request.method == 'POST':
        material.delete()
        messages.success(request, 'Material deleted successfully.')
        return redirect('material_list')
    
    return render(request, 'material_confirm_delete.html', {'material': material})

@login_required
@user_passes_test(is_technician)
def category_list(request):
    categories = MaterialCategory.objects.all()
    return render(request, 'category_list.html', {'categories': categories})

@login_required
@user_passes_test(is_technician)
def category_create(request):
    if request.method == 'POST':
        form = MaterialCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('category_list')
    else:
        form = MaterialCategoryForm()
    
    return render(request, 'category_form.html', {'form': form, 'title': 'Add Category'})

@login_required
@user_passes_test(is_technician)
def category_update(request, pk):
    category = get_object_or_404(MaterialCategory, pk=pk)
    
    if request.method == 'POST':
        form = MaterialCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('category_list')
    else:
        form = MaterialCategoryForm(instance=category)
    
    return render(request, 'category_form.html', {
        'form': form, 
        'title': 'Update Category',
        'category': category
    })

@login_required
@user_passes_test(is_technician)
def import_materials(request):
    # Lista de laboratórios e categorias existentes para referência
    existing_labs = Laboratory.objects.all()
    existing_categories = MaterialCategory.objects.all()

    if request.method == 'POST':
        form = ImportMaterialsForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            create_missing = request.POST.get('create_missing', False)
            use_default_category = request.POST.get('use_default_category', False)
            
            try:
                # Process CSV or Excel file
                if file.name.endswith('.csv'):
                    # Process CSV
                    decoded_file = file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded_file)
                    data = list(reader)
                else:
                    # Process Excel
                    wb = openpyxl.load_workbook(file)
                    ws = wb.active
                    headers = [cell.value for cell in ws[1]]

                    # Filtrar cabeçalhos vazios
                    headers = [h if h is not None else f"coluna_{i}" for i, h in enumerate(headers)]

                    data = []
                    # Encontrar a última linha com dados
                    max_row = 0
                    for i, row in enumerate(ws.iter_rows(min_row=2)):
                        if any(cell.value is not None for cell in row):
                            max_row = i + 2  # Ajustar para o índice baseado em 1 do Excel

                    for row in ws.iter_rows(min_row=2, max_row=max_row):
                        row_data = {}
                        for idx, cell in enumerate(row):
                            if idx < len(headers):
                                row_data[headers[idx]] = cell.value
                            data.append(row_data)
                
                # Import materials
                imported_count = 0
                updated_count = 0
                skipped_count = 0
                errors = []
                analyzed_count = 0  # Contador para materiais analisados

                 # Função auxiliar para verificar linhas vazias
                def is_empty_row(row):
                    return not any(value is not None and str(value).strip() for value in row.values())
                
                                # Processar apenas linhas não vazias
                valid_data = [row for row in data if not is_empty_row(row)]
                
                print(f"Total de linhas: {len(data)}, Linhas válidas: {len(valid_data)}")
                
                for idx, row in enumerate(valid_data, start=2):
                    try:
                        # Verificar se a linha está vazia (todos os valores são None, vazios ou apenas espaços)
                        if all(not str(value).strip() if value is not None else True for value in row.values()):
                            # Pular esta linha silenciosamente
                            continue

                        # Verificar campos obrigatórios
                        name = row.get('name')
                        if not name or not str(name).strip():
                            print(f"Linha {idx}: Nome vazio, pulando")
                            skipped_count += 1
                            continue            

                        # Get or create category
                        category_name = row.get('category')
                        category_type = row.get('category_type', 'consumable')  # Default to consumable
                        
                        if not category_name:
                            if use_default_category: 
                                default_category, _ = MaterialCategory.objects.get_or_create(
                                    name="Diversos", material_type="consumable"
                                )
                                category = default_category
                            else:
                                errors.append(f"Linha {idx}: Categoria não preenchida")
                                continue
                        
                        category, _ = MaterialCategory.objects.get_or_create(
                            name=category_name,
                            defaults={'material_type': category_type}
                        )
                        
                        # Get laboratory
                        lab_name = row.get('laboratory')
                        if not lab_name:
                            errors.append(f"Linha {idx}: Laboratório não está preenchido")
                            continue
                        
                        try:
                            laboratory = Laboratory.objects.get(name=lab_name)
                        except Laboratory.DoesNotExist:
                            if create_missing:
                                laboratory = Laboratory.objects.create(
                                    name=lab_name,
                                    # Valores padrão para outros campos
                                )
                            else:
                                errors.append(f"Row {idx}: Laboratory '{lab_name}' not found")
                                continue
                        
                        # Process material data
                        name = row.get('name')
                        description = row.get('description', '')
                        quantity = int(row.get('quantity', 0))
                        minimum_stock = int(row.get('minimum_stock', 0))
                        
                        if not name:
                            errors.append(f"Linha {idx}: Nome do material ausente")
                            continue
                        # Usar docling para enriquecer dados se não houver categoria
                        analyzed_data = None
                        suggested_category = ""
                        
                        if docling_service and description and (not category or not category.material_type):
                            analyzed_data = docling_service.analyze_text(description)
                            suggested_category = docling_service.categorize_material(description) or "" 
                            analyzed_count += 1
                            
                            # Se não há categoria definida, tente encontrar uma com base na sugestão
                            if not category:
                                try:
                                    category_by_suggestion = MaterialCategory.objects.filter(
                                        material_type=suggested_category
                                    ).first()
                                    
                                    if category_by_suggestion:
                                        category = category_by_suggestion
                                except:
                                    pass
                        
                        # Valor padrão se ainda não houver categoria
                        if not category:
                            default_category, _ = MaterialCategory.objects.get_or_create(
                                name="Diversos",
                                material_type="consumable"
                            )
                            category = default_category
                        
                        # Create or update material
                        material, created = Material.objects.update_or_create(
                            name=name,
                            laboratory=laboratory,
                            defaults={
                                'category': category,
                                'description': description,
                                'quantity': quantity,
                                'minimum_stock': minimum_stock,
                                'analyzed_data': analyzed_data,
                                'suggested_category': suggested_category or "",
                            }
                        )
                        
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1
                    
                    except Exception as e:
                        errors.append(f"Linha {idx}: {str(e)}")
                
                # Show results
                if imported_count > 0 or updated_count > 0:
                    success_msg = []
                    if imported_count > 0:
                        success_msg.append(f"{imported_count} novos materiais importados")
                    if updated_count > 0:
                        success_msg.append(f"{updated_count} materiais atualizados")
                    
                    messages.success(request, f"Importação concluída: {', '.join(success_msg)}.")

                if skipped_count > 0:
                    messages.info(request, f"{skipped_count} linhas vazias ou inválidas foram ignoradas.")
                    
                if analyzed_count > 0:
                    messages.info(request, f'{analyzed_count} materiais foram analisados ​​e categorizados automaticamente.')

                if errors:
                    messages.warning(request, f'Encountered {len(errors)} erros durante a importação.')
                    for error in errors[:10]:  # Show first 10 errors
                        messages.error(request, error)
                    
                    if len(errors) > 10:
                        messages.error(request, f'... e {len(errors) - 10} erros a mais.')
                
                return redirect('material_list')
            
            except Exception as e:
                messages.error(request, f'Erro ao processar arquivo: {str(e)}')
                import traceback
                traceback.print_exc()  # Imprimir o rastreamento para depuração
    else:
        form = ImportMaterialsForm()

        # Adicionar contexto para o template
    context = {
        'form': form,
        'existing_labs': existing_labs,
        'existing_categories': existing_categories,
    }
    
    return render(request, 'import_materials.html', context)

@login_required
@user_passes_test(is_technician)
def export_materials(request):
    # Get materials based on filters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    laboratory_filter = request.GET.get('laboratory', '')
    stock_status = request.GET.get('stock_status', '')
    
    materials = Material.objects.all()
    
    if search_query:
        materials = materials.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        materials = materials.filter(category__id=category_filter)
    
    if laboratory_filter:
        materials = materials.filter(laboratory__id=laboratory_filter)
    
    if stock_status == 'low':
        materials = materials.filter(quantity__lte=models.F('minimum_stock'))
    
    # Create Excel file
    output = io.BytesIO()
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Materials'
    
    # Write headers
    headers = ['Name', 'Category', 'Category Type', 'Description', 'Quantity', 
              'Minimum Stock', 'Laboratory', 'Stock Status']
    for col_num, header in enumerate(headers, 1):
        cell = worksheet.cell(row=1, column=col_num)
        cell.value = header
        cell.font = openpyxl.styles.Font(bold=True)
    
    # Write data
    for row_num, material in enumerate(materials, 2):
        worksheet.cell(row=row_num, column=1).value = material.name
        worksheet.cell(row=row_num, column=2).value = material.category.name
        worksheet.cell(row=row_num, column=3).value = material.category.get_material_type_display()
        worksheet.cell(row=row_num, column=4).value = material.description
        worksheet.cell(row=row_num, column=5).value = material.quantity
        worksheet.cell(row=row_num, column=6).value = material.minimum_stock
        worksheet.cell(row=row_num, column=7).value = material.laboratory.name
        
        stock_status = 'Low' if material.is_low_stock else 'OK'
        worksheet.cell(row=row_num, column=8).value = stock_status
    
    # Save workbook to output
    workbook.save(output)
    output.seek(0)
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=materials.xlsx'
    
    return response


@login_required
def material_detail(request, pk):
    # Fetch the material or return 404
    material = get_object_or_404(Material, pk=pk)
    
    # Fetch recent usages (you might need to create a related model or query)
    recent_usages = []  # Query for recent usage of this material
    
    context = {
        'material': material,
        'recent_usages': recent_usages
    }
    
    return render(request, 'material_detail.html', context)

@require_POST
def analyze_material_description(request):
    """API para analisar descrições de materiais em tempo real"""
    if not docling_service:
        return JsonResponse({'error': 'Serviço não disponível'}, status=400)
    
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
        
        if not description or len(description) < 10:
            return JsonResponse({'error': 'Descrição muito curta'}, status=400)
        
        # Analisar o texto
        analysis = docling_service.analyze_text(description)
        
        # Obter a categoria sugerida
        suggested_category = docling_service.categorize_material(description)
        
        # Tentar encontrar a categoria no banco de dados
        category_id = None
        category_display = dict(Material.category.field.choices).get(suggested_category, 'Consumível')
        
        try:
            category = MaterialCategory.objects.filter(material_type=suggested_category).first()
            if category:
                category_id = category.id
                category_display = category.name
        except:
            pass
        
        return JsonResponse({
            'keywords': analysis['keywords'][:10],  # Limitar a 10 palavras-chave
            'suggested_category': suggested_category,
            'suggested_category_display': category_display,
            'suggested_category_id': category_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
@user_passes_test(is_technician)
def analyze_materials_batch(request):
    """Página para analisar materiais em lote"""
    if not docling_service:
        messages.warning(request, 'O serviço de análise docling não está disponível.')
        return redirect('material_list')
    
    # Contar materiais sem análise
    unanalyzed_count = Material.objects.filter(analyzed_data__isnull=True).count()
    
    if request.method == 'POST':
        # Análise em lote
        batch_size = int(request.POST.get('batch_size', 50))
        
        materials = Material.objects.filter(
            analyzed_data__isnull=True
        )[:batch_size]
        
        analyzed_count = 0
        for material in materials:
            if material.description:
                # Analisar
                material.analyzed_data = docling_service.analyze_text(material.description)
                material.suggested_category = docling_service.categorize_material(material.description)
                material.save()
                analyzed_count += 1
        
        if analyzed_count > 0:
            messages.success(request, f'{analyzed_count} materiais foram analisados com sucesso.')
        else:
            messages.info(request, 'Nenhum material foi analisado.')
            
        return redirect('analyze_materials_batch')
    
    return render(request, 'analyze_materials_batch.html', {
        'unanalyzed_count': unanalyzed_count
    })

@require_POST
@csrf_exempt
def suggest_material_details(request):
    """API para sugerir nomes e descrições para materiais"""
    if not docling_service:
        return JsonResponse({'error': 'Serviço não disponível'}, status=400)
    
    try:
        data = json.loads(request.body)
        partial_info = data.get('partial_info', '')
        category_id = data.get('category_id')
        
        if not partial_info or len(partial_info) < 3:
            return JsonResponse({'error': 'Informação insuficiente'}, status=400)
        
        # Obter a categoria se fornecida
        category_type = None
        if category_id:
            try:
                category = MaterialCategory.objects.get(id=category_id)
                category_type = category.material_type
            except:
                pass
        
        # Usar docling para gerar sugestões
        suggestions = docling_service.generate_material_suggestions(partial_info, category_type)
        
        return JsonResponse({
            'suggestions': suggestions
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
@user_passes_test(is_technician)
def material_trends(request):
    """Visualização de tendências e insights de materiais baseados na análise docling"""
    # Inicialize as variáveis antes do bloco condicional
    materials_with_analysis = list(Material.objects.exclude(analyzed_data__isnull=True).values('id', 'name')[:100])
    similar_materials = []

    if not docling_service:
        messages.warning(request, 'O serviço de análise docling não está disponível.')
        return redirect('material_list')

    # Contar materiais analisados
    analyzed_count = Material.objects.exclude(analyzed_data__isnull=True).count()
    total_count = Material.objects.count()
    analysis_percentage = (analyzed_count / total_count * 100) if total_count > 0 else 0

    # Agrupar por categoria sugerida
    category_distribution = Material.objects.exclude(
        suggested_category__isnull=True
    ).values('suggested_category').annotate(
        count=Count('id')
    ).order_by('-count')

    # Extrair palavras-chave comuns
    common_keywords = {}
    materials_with_keywords = Material.objects.exclude(
        analyzed_data__isnull=True
    )[:100]  # Limitar para não sobrecarregar

    for material in materials_with_keywords:
        if material.analyzed_data and 'keywords' in material.analyzed_data:
            for keyword in material.analyzed_data['keywords']:
                if keyword in common_keywords:
                    common_keywords[keyword] += 1
                else:
                    common_keywords[keyword] = 1

    # Ordenar as palavras-chave pela frequência
    sorted_keywords = sorted(common_keywords.items(), key=lambda x: x[1], reverse=True)[:20]

    # Encontrar materiais similares
    if 'material_id' in request.GET:
        try:
            material_id = int(request.GET['material_id'])
            source_material = Material.objects.get(id=material_id)

            if source_material.analyzed_data and 'keywords' in source_material.analyzed_data:
                source_keywords = set(source_material.analyzed_data['keywords'])

                # Encontrar materiais com palavras-chave em comum
                other_materials = Material.objects.exclude(id=material_id).exclude(
                    analyzed_data__isnull=True
                )[:50]  # Limitar para desempenho

                for material in other_materials:
                    if material.analyzed_data and 'keywords' in material.analyzed_data:
                        material_keywords = set(material.analyzed_data['keywords'])
                        common = source_keywords.intersection(material_keywords)

                        if len(common) > 0:
                            similarity = len(common) / max(len(source_keywords), len(material_keywords))

                            similar_materials.append({
                                'material': material,
                                'similarity': similarity,
                                'common_keywords': list(common)
                            })

                # Adicionar materiais para o formulário de materiais similares
                materials_with_analysis = Material.objects.exclude(
                    analyzed_data__isnull=True
                ).values('id', 'name')[:100]  # Limitar para desempenho

                # Ordenar por similaridade
                similar_materials = sorted(similar_materials, key=lambda x: x['similarity'], reverse=True)[:5]
        except Exception as e:
            # Adicione um log de erro ou tratamento de exceção mais específico
            print(f"Erro ao processar materiais similares: {e}")

    context = {
        'analyzed_count': analyzed_count,
        'total_count': total_count,
        'analysis_percentage': analysis_percentage,
        'category_distribution': category_distribution,
        'common_keywords': sorted_keywords,
        'similar_materials': similar_materials,
        'materials_with_analysis': materials_with_analysis,
    }

    return render(request, 'material_trends.html', context)

def download_template(request):
    """Generate and serve an Excel template for material import"""
    # Create a new workbook and select the active worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template de Materiais"
    
    # Define headers
    headers = [
        "name", "category", "description", "quantity", 
        "minimum_stock", "laboratory", "category_type"
    ]
    
    # Define column widths
    column_widths = {
        "A": 30,  # name
        "B": 20,  # category
        "C": 50,  # description
        "D": 15,  # quantity
        "E": 15,  # minimum_stock
        "F": 20,  # laboratory
        "G": 15,  # category_type
    }
    
    # Apply column widths
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    # Style for headers
    header_fill = PatternFill(start_color="4A6FA5", end_color="4A6FA5", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Add headers
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
    
    # Add example data
    example_data = [
        # name, category, description, quantity, min_stock, laboratory, category_type
        ("Papel Sulfite A4", "Material de Escritório", "Papel branco para impressão, tamanho A4", 500, 100, "Laboratório 1", "consumable"),
        ("Microscópio Binocular", "Equipamentos", "Microscópio para visualização de amostras", 5, 2, "Laboratório 2", "permanent"),
        ("Reagente Químico", "Reagentes", "Reagente para análises químicas", 20, 5, "Laboratório 3", "perishable"),
    ]
    
    # Add example data to worksheet
    for row_idx, row_data in enumerate(example_data, 2):
        for col_idx, cell_value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx).value = cell_value
    
    # Add notes
    notes_row = len(example_data) + 3
    ws.cell(row=notes_row, column=1).value = "Notas:"
    ws.cell(row=notes_row, column=1).font = Font(bold=True)
    
    notes = [
        "- Obrigatório: name, category, quantity, minimum_stock, laboratory",
        "- Opcional: description, category_type",
        "- category_type pode ser: consumable, permanent, perishable",
        "- Use nomes de laboratórios e categorias que já existem no sistema",
        "- A primeira linha (cabeçalho) será ignorada durante a importação"
    ]
    
    for i, note in enumerate(notes, 1):
        ws.cell(row=notes_row + i, column=1).value = note
        ws.merge_cells(f'A{notes_row + i}:G{notes_row + i}')
    
    # Save to output stream
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=template_materiais.xlsx'
    
    return response

