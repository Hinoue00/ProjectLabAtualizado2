# inventory/automation_service.py
# Importações condicionais para automação
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import numpy as np
except ImportError:
    np = None
from typing import Dict, List, Tuple, Any, Optional
from django.conf import settings
from django.db import transaction
from .models import Material, MaterialCategory
from laboratories.models import Laboratory
from .services import DoclingService
import logging
import re

logger = logging.getLogger(__name__)

class InventoryAutomationService:
    """
    Serviço para automação completa do sistema de inventário
    Processa arquivos Excel e organiza automaticamente os dados
    """
    
    def __init__(self):
        self.docling_service = DoclingService()
        self.required_columns = ['name', 'quantity', 'minimum_stock']
        self.optional_columns = ['description', 'category', 'laboratory', 'category_type']
        self.stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'categorized': 0
        }
    
    def process_excel_file(self, file_path: str) -> Dict[str, Any]:
        """
        Processa arquivo Excel e organiza automaticamente o inventário
        """
        try:
            # Ler arquivo Excel
            df = self._read_excel_file(file_path)
            
            # Validar e normalizar dados
            df_cleaned = self._clean_and_validate_data(df)
            
            # Enriquecer dados com análise automática
            df_enriched = self._enrich_data_with_analysis(df_cleaned)
            
            # Criar/atualizar materiais no banco de dados
            results = self._save_materials_to_database(df_enriched)
            
            return {
                'success': True,
                'stats': self.stats,
                'results': results,
                'message': f'Processados {self.stats["processed"]} itens, {self.stats["created"]} criados, {self.stats["updated"]} atualizados'
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo Excel: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    def _read_excel_file(self, file_path: str) -> pd.DataFrame:
        """Lê arquivo Excel e detecta automaticamente a estrutura"""
        
        # Tentar diferentes formatos de arquivo
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path, sheet_name=0)
        except UnicodeDecodeError:
            # Tentar com encoding diferente
            df = pd.read_csv(file_path, encoding='latin-1')
        
        # Normalizar nomes das colunas
        df.columns = [self._normalize_column_name(col) for col in df.columns]
        
        return df
    
    def _normalize_column_name(self, column_name: str) -> str:
        """Normaliza nomes de colunas para padrão interno"""
        
        # Mapeamento de nomes comuns
        column_mapping = {
            'nome': 'name',
            'material': 'name',
            'item': 'name',
            'produto': 'name',
            
            'descricao': 'description',
            'descrição': 'description',
            'detalhes': 'description',
            
            'categoria': 'category',
            'tipo': 'category',
            'classe': 'category',
            
            'quantidade': 'quantity',
            'qtd': 'quantity',
            'estoque': 'quantity',
            'qty': 'quantity',
            
            'minimo': 'minimum_stock',
            'estoque_minimo': 'minimum_stock',
            'min_stock': 'minimum_stock',
            'limite': 'minimum_stock',
            
            'laboratorio': 'laboratory',
            'laboratório': 'laboratory',
            'lab': 'laboratory',
            'local': 'laboratory',
            
            'tipo_categoria': 'category_type',
            'tipo_material': 'category_type'
        }
        
        normalized = column_name.lower().strip()
        normalized = re.sub(r'[^a-z0-9_]', '_', normalized)
        
        return column_mapping.get(normalized, normalized)
    
    def _clean_and_validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e valida os dados do DataFrame"""
        
        # Verificar colunas obrigatórias
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            # Tentar mapear colunas automaticamente
            df = self._auto_map_columns(df)
            
            # Verificar novamente
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")
        
        # Remover linhas completamente vazias
        df = df.dropna(how='all')
        
        # Limpar dados
        df['name'] = df['name'].astype(str).str.strip()
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
        df['minimum_stock'] = pd.to_numeric(df['minimum_stock'], errors='coerce').fillna(1).astype(int)
        
        # Limpar campos opcionais
        if 'description' in df.columns:
            df['description'] = df['description'].astype(str).str.strip()
            df['description'] = df['description'].replace('nan', '')
        
        if 'category' in df.columns:
            df['category'] = df['category'].astype(str).str.strip()
            df['category'] = df['category'].replace('nan', '')
        
        if 'laboratory' in df.columns:
            df['laboratory'] = df['laboratory'].astype(str).str.strip()
            df['laboratory'] = df['laboratory'].replace('nan', '')
        
        # Remover linhas sem nome
        df = df[df['name'] != 'nan']
        df = df[df['name'] != '']
        
        return df
    
    def _auto_map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mapeia automaticamente colunas baseado no conteúdo"""
        
        # Analisar primeira linha de dados para identificar padrões
        for col in df.columns:
            sample_data = df[col].dropna().head(5).astype(str)
            
            # Detectar coluna de quantidade (números)
            if col not in ['quantity', 'minimum_stock'] and sample_data.str.isnumeric().all():
                if 'quantity' not in df.columns:
                    df = df.rename(columns={col: 'quantity'})
                elif 'minimum_stock' not in df.columns:
                    df = df.rename(columns={col: 'minimum_stock'})
            
            # Detectar coluna de nome (textos longos)
            elif 'name' not in df.columns and sample_data.str.len().mean() > 5:
                df = df.rename(columns={col: 'name'})
        
        return df
    
    def _enrich_data_with_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enriquece dados com análise automática do Docling"""
        
        enriched_rows = []
        
        for index, row in df.iterrows():
            enriched_row = row.copy()
            
            # Analisar descrição se disponível
            description = str(row.get('description', ''))
            name = str(row.get('name', ''))
            
            # Criar descrição automática se não existir
            if not description or description == 'nan' or description == '':
                description = self._generate_description(name)
                enriched_row['description'] = description
            
            # Analisar com Docling
            analysis = self.docling_service.analyze_text(description)
            
            # Sugerir categoria se não especificada
            if not row.get('category') or str(row.get('category')) == 'nan':
                suggested_category = self.docling_service.categorize_material(description)
                category_obj = self._get_or_create_category(name, suggested_category)
                enriched_row['category'] = category_obj.name
                enriched_row['category_type'] = suggested_category
                self.stats['categorized'] += 1
            
            # Definir laboratório padrão se não especificado
            if not row.get('laboratory') or str(row.get('laboratory')) == 'nan':
                lab = self._assign_default_laboratory(name, description)
                enriched_row['laboratory'] = lab.name
            
            # Adicionar dados de análise
            enriched_row['analyzed_data'] = analysis
            
            enriched_rows.append(enriched_row)
        
        return pd.DataFrame(enriched_rows)
    
    def _generate_description(self, name: str) -> str:
        """Gera descrição automática baseada no nome"""
        
        # Templates de descrição por tipo de material
        templates = {
            'papel': 'Papel para uso geral em escritório e laboratório',
            'caneta': 'Caneta para escrita e anotações',
            'microscópio': 'Equipamento para visualização de amostras microscópicas',
            'computador': 'Equipamento de informática para atividades administrativas',
            'reagente': 'Reagente químico para análises laboratoriais',
            'vidraria': 'Material de vidro para experimentos',
        }
        
        name_lower = name.lower()
        
        for keyword, template in templates.items():
            if keyword in name_lower:
                return f"{name} - {template}"
        
        return f"{name} - Material para uso em laboratório"
    
    def _get_or_create_category(self, material_name: str, category_type: str) -> MaterialCategory:
        """Obtém ou cria categoria automaticamente"""
        
        # Mapear nomes de categoria baseado no tipo
        category_names = {
            'consumable': 'Material de Consumo',
            'permanent': 'Equipamentos',
            'perishable': 'Material Perecível'
        }
        
        # Tentar ser mais específico baseado no nome do material
        specific_categories = {
            'papel': ('Material de Escritório', 'consumable'),
            'caneta': ('Material de Escritório', 'consumable'),
            'microscópio': ('Equipamentos de Laboratório', 'permanent'),
            'computador': ('Equipamentos de Informática', 'permanent'),
            'reagente': ('Reagentes Químicos', 'consumable'),
            'medicamento': ('Produtos Farmacêuticos', 'perishable'),
        }
        
        material_lower = material_name.lower()
        category_name = category_names.get(category_type, 'Material Geral')
        
        # Buscar categoria mais específica
        for keyword, (specific_name, specific_type) in specific_categories.items():
            if keyword in material_lower:
                category_name = specific_name
                category_type = specific_type
                break
        
        # Buscar ou criar categoria
        category, created = MaterialCategory.objects.get_or_create(
            name=category_name,
            defaults={'material_type': category_type}
        )
        
        return category
    
    def _assign_default_laboratory(self, name: str, description: str) -> Laboratory:
        """Atribui laboratório padrão baseado no tipo de material"""
        
        # Mapear materiais para laboratórios
        lab_mapping = {
            'informática': ['computador', 'notebook', 'mouse', 'teclado', 'monitor'],
            'química': ['reagente', 'ácido', 'base', 'solução'],
            'biologia': ['microscópio', 'amostra', 'cultura', 'biológico'],
            'física': ['equipamento', 'aparelho', 'instrumento'],
        }
        
        text_to_analyze = f"{name} {description}".lower()
        
        for lab_type, keywords in lab_mapping.items():
            for keyword in keywords:
                if keyword in text_to_analyze:
                    # Buscar laboratório do tipo
                    lab = Laboratory.objects.filter(
                        name__icontains=lab_type
                    ).first()
                    if lab:
                        return lab
        
        # Retornar primeiro laboratório disponível como padrão
        return Laboratory.objects.first()
    
    def _save_materials_to_database(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Salva materiais no banco de dados"""
        
        results = []
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    result = self._create_or_update_material(row)
                    results.append(result)
                    self.stats['processed'] += 1
                    
                    if result['action'] == 'created':
                        self.stats['created'] += 1
                    elif result['action'] == 'updated':
                        self.stats['updated'] += 1
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    results.append({
                        'row': index + 2,
                        'name': row.get('name', 'N/A'),
                        'action': 'error',
                        'error': str(e)
                    })
        
        return results
    
    def _create_or_update_material(self, row: pd.Series) -> Dict[str, Any]:
        """Cria ou atualiza um material"""
        
        name = row['name']
        description = row.get('description', '')
        quantity = int(row['quantity'])
        minimum_stock = int(row['minimum_stock'])
        
        # Buscar categoria
        category_name = row.get('category', 'Material Geral')
        category = MaterialCategory.objects.filter(name=category_name).first()
        if not category:
            category_type = row.get('category_type', 'consumable')
            category = MaterialCategory.objects.create(
                name=category_name,
                material_type=category_type
            )
        
        # Buscar laboratório
        lab_name = row.get('laboratory', '')
        laboratory = Laboratory.objects.filter(name__icontains=lab_name).first()
        if not laboratory:
            laboratory = Laboratory.objects.first()
        
        # Verificar se material já existe
        existing_material = Material.objects.filter(
            name__iexact=name,
            laboratory=laboratory
        ).first()
        
        analyzed_data = row.get('analyzed_data', {})
        
        if existing_material:
            # Atualizar material existente
            existing_material.description = description
            existing_material.quantity = quantity
            existing_material.minimum_stock = minimum_stock
            existing_material.category = category
            existing_material.analyzed_data = analyzed_data
            existing_material.save()
            
            return {
                'row': None,
                'name': name,
                'action': 'updated',
                'material_id': existing_material.id
            }
        else:
            # Criar novo material
            material = Material.objects.create(
                name=name,
                description=description,
                quantity=quantity,
                minimum_stock=minimum_stock,
                category=category,
                laboratory=laboratory,
                analyzed_data=analyzed_data
            )
            
            return {
                'row': None,
                'name': name,
                'action': 'created',
                'material_id': material.id
            }
    
    def generate_template_excel(self) -> str:
        """Gera template Excel para importação"""
        
        # Criar DataFrame com exemplo
        template_data = {
            'name': [
                'Papel A4',
                'Microscópio Binocular',
                'Reagente Químico XYZ',
                'Computador Desktop',
                'Luvas Descartáveis'
            ],
            'description': [
                'Papel branco para impressão, tamanho A4',
                'Microscópio para visualização de amostras microscópicas',
                'Reagente para análises químicas específicas',
                'Computador para atividades administrativas',
                'Luvas de proteção descartáveis'
            ],
            'quantity': [500, 3, 50, 10, 1000],
            'minimum_stock': [100, 1, 10, 2, 200],
            'category': [
                'Material de Escritório',
                'Equipamentos de Laboratório', 
                'Reagentes Químicos',
                'Equipamentos de Informática',
                'Material de Proteção'
            ],
            'category_type': [
                'consumable',
                'permanent',
                'consumable', 
                'permanent',
                'consumable'
            ],
            'laboratory': [
                'Laboratório Geral',
                'Laboratório de Biologia',
                'Laboratório de Química',
                'Laboratório de Informática',
                'Laboratório Geral'
            ]
        }
        
        df = pd.DataFrame(template_data)
        
        # Salvar template
        template_path = '/tmp/template_inventario_labconnect.xlsx'
        with pd.ExcelWriter(template_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Materiais', index=False)
            
            # Adicionar planilha de instruções
            instructions = pd.DataFrame({
                'Instruções de Uso': [
                    '1. Preencha a planilha "Materiais" com os dados do seu inventário',
                    '2. Colunas obrigatórias: name, quantity, minimum_stock',
                    '3. Colunas opcionais: description, category, category_type, laboratory',
                    '4. category_type pode ser: consumable, permanent, perishable',
                    '5. Se não especificar categoria, o sistema sugerirá automaticamente',
                    '6. Se não especificar laboratório, será atribuído automaticamente',
                    '7. O sistema criará categorias e laboratórios automaticamente se não existirem',
                    '8. Salve o arquivo e faça upload no sistema LabConnect'
                ]
            })
            instructions.to_excel(writer, sheet_name='Instruções', index=False)
        
        return template_path
    
    def validate_excel_structure(self, file_path: str) -> Dict[str, Any]:
        """Valida estrutura do arquivo Excel antes do processamento"""
        
        try:
            df = self._read_excel_file(file_path)
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'stats': {
                    'total_rows': len(df),
                    'columns_found': list(df.columns),
                    'required_columns_missing': [],
                    'optional_columns_missing': []
                }
            }
            
            # Verificar colunas obrigatórias
            normalized_columns = [self._normalize_column_name(col) for col in df.columns]
            
            for required_col in self.required_columns:
                if required_col not in normalized_columns:
                    validation_result['stats']['required_columns_missing'].append(required_col)
                    validation_result['errors'].append(f'Coluna obrigatória ausente: {required_col}')
            
            # Verificar colunas opcionais
            for optional_col in self.optional_columns:
                if optional_col not in normalized_columns:
                    validation_result['stats']['optional_columns_missing'].append(optional_col)
                    validation_result['warnings'].append(f'Coluna opcional ausente: {optional_col} (será preenchida automaticamente)')
            
            # Verificar dados
            if len(df) == 0:
                validation_result['errors'].append('Arquivo está vazio')
            
            # Verificar se há pelo menos uma linha com dados válidos
            if 'name' in normalized_columns:
                name_col_index = normalized_columns.index('name')
                actual_name_col = df.columns[name_col_index]
                valid_names = df[actual_name_col].dropna()
                if len(valid_names) == 0:
                    validation_result['errors'].append('Nenhum material válido encontrado')
            
            if validation_result['errors']:
                validation_result['valid'] = False
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Erro ao ler arquivo: {str(e)}'],
                'warnings': [],
                'stats': {}
            }