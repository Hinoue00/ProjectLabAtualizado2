# inventory/ai_inventory_organizer.py - Versão MELHORADA para estruturas complexas

# Importações condicionais para AI
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
import logging
import re
import json

logger = logging.getLogger(__name__)

class AIInventoryOrganizer:
    """
    Sistema de IA para organização automática de inventário
    VERSÃO MELHORADA - Detecta estruturas complexas de planilhas
    """
    
    def __init__(self):
        self.ai_categories = {
            # Equipamentos de Laboratório
            'equipamentos': {
                'keywords': ['microscópio', 'balança', 'estufa', 'autoclave', 'centrífuga', 'pipeta', 'buretas', 'provetas', 'capela', 'camera', 'termociclador', 'lupa', 'agitador'],
                'category': 'Equipamentos de Laboratório',
                'type': 'permanent',
                'default_lab': 'Laboratório Geral'
            },
            
            # Material Anatômico/Médico
            'anatomia': {
                'keywords': ['anatomia', 'esqueleto', 'modelo', 'torso', 'musculo', 'coração', 'encéfalo', 'circulatório', 'cardiorespiratório'],
                'category': 'Material Anatômico',
                'type': 'permanent',
                'default_lab': 'Laboratório de Anatomia'
            },
            
            # Microbiologia
            'microbiologia': {
                'keywords': ['microbiologia', 'cultura', 'meio', 'petri', 'autoclave', 'esterilização', 'asseptica'],
                'category': 'Material de Microbiologia',
                'type': 'consumable',
                'default_lab': 'Laboratório de Microbiologia'
            },
            
            # Reagentes Químicos
            'reagentes': {
                'keywords': ['ácido', 'base', 'sal', 'solvente', 'reagente', 'químico', 'solução', 'ph'],
                'category': 'Reagentes Químicos',
                'type': 'consumable',
                'default_lab': 'Laboratório de Química'
            },
            
            # Material de Escritório
            'escritorio': {
                'keywords': ['papel', 'caneta', 'lápis', 'borracha', 'grampeador', 'pasta', 'arquivo'],
                'category': 'Material de Escritório',
                'type': 'consumable',
                'default_lab': 'Laboratório Geral'
            },
            
            # Equipamentos de Informática
            'informatica': {
                'keywords': ['computador', 'notebook', 'mouse', 'teclado', 'monitor', 'impressora', 'cabo'],
                'category': 'Equipamentos de Informática',
                'type': 'permanent',
                'default_lab': 'Laboratório de Informática'
            },
            
            # Vidraria
            'vidraria': {
                'keywords': ['béquer', 'erlenmeyer', 'proveta', 'pipeta', 'bureta', 'vidro', 'tubo'],
                'category': 'Vidraria de Laboratório',
                'type': 'permanent',
                'default_lab': 'Laboratório de Química'
            }
        }
        
        self.stats = {
            'total_processed': 0,
            'auto_categorized': 0,
            'auto_assigned_lab': 0,
            'descriptions_generated': 0,
            'duplicates_found': 0,
            'errors': 0,
            'structure_detected': 'unknown'
        }
    
    def _detect_complex_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detecta estruturas complexas de planilhas que não seguem padrão tradicional
        """
        print(f"DEBUG: Analisando estrutura da planilha - Shape: {df.shape}")
        print(f"DEBUG: Colunas: {list(df.columns)}")
        print(f"DEBUG: Primeiras 5 linhas:")
        print(df.head().to_string())
        
        detected_columns = []
        
        # Analisar cada coluna para encontrar padrões
        for col_idx, col_name in enumerate(df.columns):
            col_data = df[col_name].dropna()
            
            # Pular colunas completamente vazias
            if len(col_data) == 0:
                continue
            
            # Analisar tipos de dados na coluna
            string_count = sum(1 for x in col_data if isinstance(x, str) and len(str(x).strip()) > 2)
            numeric_count = sum(1 for x in col_data if isinstance(x, (int, float)) and x > 0)
            
            print(f"DEBUG: Coluna {col_idx} ({col_name}): {string_count} strings, {numeric_count} números")
            
            # Detectar colunas de material (muitas strings descritivas)
            if string_count > 3 and string_count > numeric_count:
                # Verificar se são nomes de materiais (palavras relacionadas a laboratório)
                sample_text = ' '.join(str(x).lower() for x in col_data[:10] if isinstance(x, str))
                lab_keywords = ['modelo', 'equipamento', 'material', 'sistema', 'aparelho', 'instrumento', 'capela', 'estufa', 'microscópio', 'anatomia']
                
                if any(keyword in sample_text for keyword in lab_keywords):
                    detected_columns.append({
                        'index': col_idx,
                        'name': col_name,
                        'type': 'material_name',
                        'data_count': string_count,
                        'sample_data': list(col_data.head())
                    })
            
            # Detectar colunas de quantidade (números pequenos positivos)
            elif numeric_count > 3 and all(isinstance(x, (int, float)) and 0 < x < 1000 for x in col_data if pd.notna(x)):
                detected_columns.append({
                    'index': col_idx,
                    'name': col_name,
                    'type': 'quantity',
                    'data_count': numeric_count,
                    'sample_data': list(col_data.head())
                })
        
        print(f"DEBUG: Colunas detectadas: {detected_columns}")
        return {'detected_columns': detected_columns}
    
    def _extract_materials_from_complex_structure(self, df: pd.DataFrame, structure_info: Dict) -> pd.DataFrame:
        """
        Extrai materiais de estruturas complexas detectadas
        """
        detected_columns = structure_info['detected_columns']
        
        # Agrupar colunas por tipo
        material_columns = [col for col in detected_columns if col['type'] == 'material_name']
        quantity_columns = [col for col in detected_columns if col['type'] == 'quantity']
        
        print(f"DEBUG: Colunas de material: {len(material_columns)}")
        print(f"DEBUG: Colunas de quantidade: {len(quantity_columns)}")
        
        all_materials = []
        
        # Processar cada par material-quantidade
        for mat_col in material_columns:
            mat_col_name = mat_col['name']
            
            # Encontrar coluna de quantidade mais próxima
            closest_qty_col = None
            min_distance = float('inf')
            
            for qty_col in quantity_columns:
                distance = abs(mat_col['index'] - qty_col['index'])
                if distance < min_distance:
                    min_distance = distance
                    closest_qty_col = qty_col
            
            print(f"DEBUG: Processando coluna {mat_col_name} com quantidade {closest_qty_col['name'] if closest_qty_col else 'N/A'}")
            
            # Extrair materiais desta coluna
            for idx, row in df.iterrows():
                material_name = row.get(mat_col_name)
                
                # Verificar se é um nome de material válido
                if pd.notna(material_name) and isinstance(material_name, str) and len(str(material_name).strip()) > 2:
                    material_name = str(material_name).strip()
                    
                    # Pular cabeçalhos ou títulos
                    if material_name.lower() in ['materiais', 'material', 'nome', 'produto', 'item', 'anatomia', 'microbiologia']:
                        continue
                    
                    # Obter quantidade
                    quantity = 1  # Padrão
                    if closest_qty_col:
                        qty_value = row.get(closest_qty_col['name'])
                        if pd.notna(qty_value) and isinstance(qty_value, (int, float)) and qty_value > 0:
                            quantity = int(qty_value)
                    
                    # Detectar laboratório baseado na posição/contexto
                    laboratorio = self._detect_lab_from_context(material_name, mat_col, df, idx)
                    
                    all_materials.append({
                        'nome': material_name,
                        'quantidade': quantity,
                        'estoque_minimo': 1,
                        'categoria': '',  # Será preenchido pela IA
                        'laboratorio': laboratorio,
                        'descricao': '',  # Será preenchido pela IA
                        'source_column': mat_col_name,
                        'source_row': idx
                    })
        
        print(f"DEBUG: Total de materiais extraídos: {len(all_materials)}")
        
        if not all_materials:
            return pd.DataFrame()
        
        # Converter para DataFrame
        materials_df = pd.DataFrame(all_materials)
        return materials_df
    
    def _detect_lab_from_context(self, material_name: str, mat_col: Dict, df: pd.DataFrame, row_idx: int) -> str:
        """
        Detecta laboratório baseado no contexto da planilha
        """
        # Procurar por títulos/cabeçalhos próximos que indiquem o laboratório
        material_lower = material_name.lower()
        
        # Verificar algumas linhas acima para encontrar títulos de seção
        for check_row in range(max(0, row_idx - 10), row_idx):
            for col in df.columns:
                cell_value = df.iloc[check_row, df.columns.get_loc(col)]
                if pd.notna(cell_value) and isinstance(cell_value, str):
                    cell_lower = str(cell_value).lower()
                    
                    # Buscar indicadores de laboratório
                    if 'anatomia' in cell_lower:
                        return 'Laboratório de Anatomia'
                    elif 'microbiologia' in cell_lower:
                        return 'Laboratório de Microbiologia'
                    elif 'química' in cell_lower or 'quimica' in cell_lower:
                        return 'Laboratório de Química'
                    elif 'biologia' in cell_lower:
                        return 'Laboratório de Biologia'
                    elif 'física' in cell_lower or 'fisica' in cell_lower:
                        return 'Laboratório de Física'
        
        # Análise baseada no próprio material
        if any(word in material_lower for word in ['anatomia', 'esqueleto', 'modelo', 'torso', 'músculo', 'coração', 'encéfalo']):
            return 'Laboratório de Anatomia'
        elif any(word in material_lower for word in ['capela', 'estufa', 'autoclave', 'cultura', 'asseptica']):
            return 'Laboratório de Microbiologia'
        elif any(word in material_lower for word in ['químico', 'reagente', 'ácido', 'solução']):
            return 'Laboratório de Química'
        
        return 'Laboratório Geral'
    
    def get_organization_preview(self, file_path: str) -> Dict[str, Any]:
        """
        Gera preview da organização para estruturas complexas - MELHORADO
        """
        try:
            # 1. Ler arquivo
            df = self._read_and_analyze_excel(file_path)
            
            # 2. Detectar estrutura complexa
            structure_info = self._detect_complex_structure(df)
            
            # 3. Extrair materiais da estrutura complexa
            materials_df = self._extract_materials_from_complex_structure(df, structure_info)
            
            if materials_df.empty:
                return {
                    'success': False,
                    'error': 'Nenhum material foi detectado na planilha. Verifique se a estrutura está correta.',
                    'debug_info': {
                        'original_shape': df.shape,
                        'detected_columns': structure_info.get('detected_columns', []),
                        'sample_data': df.head(3).to_dict('records') if not df.empty else []
                    }
                }
            
            # 4. Aplicar IA para organização
            materials_organized = self._apply_ai_organization(materials_df, {})
            
            # 5. Preparar preview
            preview_columns = ['nome', 'categoria', 'laboratorio', 'quantidade', 'estoque_minimo']
            for col in preview_columns:
                if col not in materials_organized.columns:
                    materials_organized[col] = 'N/A'
            
            preview_data = materials_organized[preview_columns].head(10).to_dict('records')
            
            # 6. Detectar mapeamento de colunas
            detected_mapping = {}
            for col_info in structure_info['detected_columns']:
                if col_info['type'] == 'material_name':
                    detected_mapping['nome'] = col_info['name']
                elif col_info['type'] == 'quantity':
                    detected_mapping['quantidade'] = col_info['name']
            
            self.stats['total_processed'] = len(materials_organized)
            self.stats['structure_detected'] = 'complex_multi_column'
            
            return {
                'success': True,
                'preview': preview_data,
                'total_rows': len(materials_organized),
                'column_mapping': detected_mapping,
                'stats': self.stats,
                'structure_info': {
                    'type': 'complex',
                    'detected_columns': len(structure_info['detected_columns']),
                    'material_columns': len([c for c in structure_info['detected_columns'] if c['type'] == 'material_name'])
                }
            }
            
        except Exception as e:
            logger.error(f"Erro no preview: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao gerar preview: {str(e)}"
            }
    
    def organize_inventory_from_excel(self, file_path: str, options: Dict = None) -> Dict[str, Any]:
        """
        Organiza inventário de estruturas complexas - MELHORADO
        """
        options = options or {}
        
        try:
            # 1. Ler e detectar estrutura
            df = self._read_and_analyze_excel(file_path)
            structure_info = self._detect_complex_structure(df)
            
            # 2. Extrair materiais
            materials_df = self._extract_materials_from_complex_structure(df, structure_info)
            
            if materials_df.empty:
                return {
                    'success': False,
                    'error': 'Nenhum material detectado na planilha',
                    'stats': self.stats
                }
            
            # 3. Aplicar IA
            df_organized = self._apply_ai_organization(materials_df, options)
            
            # 4. Detectar duplicatas
            df_deduplicated = self._detect_and_handle_duplicates(df_organized, options)
            
            # 5. Validar dados
            df_validated = self._validate_final_data(df_deduplicated)
            
            # 6. Salvar no banco
            results = self._save_organized_data(df_validated, options)
            
            return {
                'success': True,
                'stats': self.stats,
                'results': results,
                'organized_data': df_validated.to_dict('records'),
                'message': self._generate_success_message()
            }
            
        except Exception as e:
            logger.error(f"Erro na organização: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    # Manter todos os outros métodos da versão anterior
    def _read_and_analyze_excel(self, file_path: str) -> pd.DataFrame:
        """Lê planilha - Mantido da versão anterior"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                df = pd.read_excel(file_path)
        except Exception as e:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, encoding='latin-1')
                else:
                    df = pd.read_excel(file_path, engine='openpyxl')
            except Exception as e2:
                raise Exception(f"Erro ao ler arquivo: {str(e2)}")
        
        df.columns = df.columns.astype(str)
        df = df.dropna(how='all')
        
        logger.info(f"Planilha carregada: {len(df)} linhas, {len(df.columns)} colunas")
        return df
    
    def _apply_ai_organization(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        """Aplica IA - Mantido da versão anterior"""
        organized_rows = []
        
        for idx, row in df.iterrows():
            try:
                organized_row = row.copy()
                nome = str(row.get('nome', '')).lower()
                descricao = str(row.get('descricao', '')).lower()
                
                # Categorização automática
                if not str(row.get('categoria')).strip() or str(row.get('categoria')).lower() in ['nan', 'none', '']:
                    categoria_info = self._categorize_with_ai(nome, descricao)
                    organized_row['categoria'] = categoria_info['category']
                    organized_row['tipo_categoria'] = categoria_info['type']
                    self.stats['auto_categorized'] += 1
                
                # Atribuição de laboratório
                if not str(row.get('laboratorio')).strip() or str(row.get('laboratorio')).lower() in ['nan', 'none', '']:
                    laboratorio = self._assign_laboratory_with_ai(nome, descricao, organized_row.get('categoria'))
                    organized_row['laboratorio'] = laboratorio
                    self.stats['auto_assigned_lab'] += 1
                
                # Geração de descrição
                if not str(row.get('descricao')).strip() or str(row.get('descricao')).lower() in ['nan', 'none', '']:
                    descricao_gerada = self._generate_description_with_ai(nome, organized_row.get('categoria'))
                    organized_row['descricao'] = descricao_gerada
                    self.stats['descriptions_generated'] += 1
                
                # Valores padrão
                if pd.isna(row.get('quantidade')) or row.get('quantidade') == 0:
                    organized_row['quantidade'] = 1
                
                if pd.isna(row.get('estoque_minimo')) or row.get('estoque_minimo') == 0:
                    organized_row['estoque_minimo'] = 1
                
                organized_rows.append(organized_row)
                
            except Exception as e:
                logger.error(f"Erro ao processar linha {idx}: {e}")
                organized_rows.append(row)
                self.stats['errors'] += 1
        
        return pd.DataFrame(organized_rows)
    
    def _categorize_with_ai(self, nome: str, descricao: str) -> Dict[str, str]:
        """Categoriza com IA - Mantido da versão anterior"""
        texto_completo = f"{nome} {descricao}".lower()
        
        for categoria_key, categoria_info in self.ai_categories.items():
            for keyword in categoria_info['keywords']:
                if keyword in texto_completo:
                    return {
                        'category': categoria_info['category'],
                        'type': categoria_info['type']
                    }
        
        if any(word in texto_completo for word in ['digital', 'eletrônico', 'software']):
            return {'category': 'Equipamentos de Informática', 'type': 'permanent'}
        elif any(word in texto_completo for word in ['descartável', 'consumível']):
            return {'category': 'Material de Consumo', 'type': 'consumable'}
        elif any(word in texto_completo for word in ['equipamento', 'instrumento']):
            return {'category': 'Equipamentos de Laboratório', 'type': 'permanent'}
        
        return {'category': 'Material Geral', 'type': 'consumable'}
    
    def _assign_laboratory_with_ai(self, nome: str, descricao: str, categoria: str) -> str:
        """Atribui laboratório - Mantido da versão anterior"""
        texto_completo = f"{nome} {descricao} {categoria}".lower()
        
        category_to_lab = {
            'anatomia': 'Laboratório de Anatomia',
            'microbiologia': 'Laboratório de Microbiologia',
            'química': 'Laboratório de Química',
            'biologia': 'Laboratório de Biologia',
            'informática': 'Laboratório de Informática',
            'física': 'Laboratório de Física',
            'engenharia': 'Laboratório de Engenharia',
            'saúde': 'Laboratório de Saúde'
        }
        
        for key, lab in category_to_lab.items():
            if key in texto_completo:
                return lab
        
        for categoria_key, categoria_info in self.ai_categories.items():
            for keyword in categoria_info['keywords']:
                if keyword in texto_completo:
                    return categoria_info['default_lab']
        
        return 'Laboratório Geral'
    
    def _generate_description_with_ai(self, nome: str, categoria: str) -> str:
        """Gera descrição - Mantido da versão anterior"""
        templates = {
            'Material Anatômico': f"{nome} - Material anatômico para estudos e demonstrações em aulas práticas",
            'Material de Microbiologia': f"{nome} - Equipamento para análises microbiológicas e culturas",
            'Equipamentos de Laboratório': f"{nome} - Equipamento para uso em laboratório e análises científicas",
            'Reagentes Químicos': f"{nome} - Reagente químico para análises e experimentos laboratoriais",
            'Material de Escritório': f"{nome} - Material para uso administrativo e documentação",
            'Equipamentos de Informática': f"{nome} - Equipamento de informática para atividades computacionais",
            'Vidraria de Laboratório': f"{nome} - Vidraria para experimentos e análises laboratoriais"
        }
        
        return templates.get(str(categoria), f"{nome} - Material para uso em laboratório")
    
    # Manter outros métodos necessários da versão anterior
    def _detect_and_handle_duplicates(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        return df  # Simplificado para esta versão
    
    def _validate_final_data(self, df: pd.DataFrame) -> pd.DataFrame:
        required_columns = ['nome', 'categoria', 'laboratorio', 'quantidade', 'estoque_minimo']
        
        for col in required_columns:
            if col not in df.columns:
                if col in ['categoria', 'laboratorio']:
                    df[col] = 'Não Definido'
                else:
                    df[col] = 1
        
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce').fillna(1)
        df['estoque_minimo'] = pd.to_numeric(df['estoque_minimo'], errors='coerce').fillna(1)
        df['estoque_minimo'] = df['estoque_minimo'].apply(lambda x: max(1, int(x)))
        df['quantidade'] = df['quantidade'].apply(lambda x: max(0, int(x)))
        
        for col in ['nome', 'categoria', 'laboratorio']:
            if col in df.columns:
                df[col] = df[col].astype(str)
                df[col] = df[col].replace(['nan', 'None', 'NaN'], 'Não Definido')
        
        return df
    
    def _save_organized_data(self, df: pd.DataFrame, options: Dict) -> List[Dict]:
        results = []
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    categoria, _ = MaterialCategory.objects.get_or_create(
                        name=str(row['categoria']),
                        defaults={'material_type': row.get('tipo_categoria', 'consumable')}
                    )
                    
                    laboratorio, _ = Laboratory.objects.get_or_create(
                        name=str(row['laboratorio']),
                        defaults={
                            'location': f"Localização {row['laboratorio']}",
                            'capacity': 30,
                            'is_active': True
                        }
                    )
                    
                    material, created = Material.objects.update_or_create(
                        name=str(row['nome']),
                        laboratory=laboratorio,
                        defaults={
                            'category': categoria,
                            'description': str(row.get('descricao', '')),
                            'quantity': int(row['quantidade']),
                            'minimum_stock': int(row['estoque_minimo']),
                            'analyzed_data': {
                                'ai_processed': True,
                                'auto_categorized': True,
                                'confidence': 0.9,
                                'structure_type': 'complex'
                            }
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    results.append({
                        'name': material.name,
                        'category': categoria.name,
                        'laboratory': laboratorio.name,
                        'action': 'created' if created else 'updated'
                    })
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Erro ao salvar material {row.get('nome', 'N/A')}: {str(e)}")
        
        self.stats['created'] = created_count
        self.stats['updated'] = updated_count
        
        return results
    
    def _generate_success_message(self) -> str:
        """Gera mensagem de sucesso com estatísticas"""
        return (f"Organização automática concluída! "
                f"{self.stats['total_processed']} materiais processados, "
                f"{self.stats['created']} criados, "
                f"{self.stats['updated']} atualizados. "
                f"IA aplicada: {self.stats['auto_categorized']} categorizações automáticas, "
                f"{self.stats['auto_assigned_lab']} laboratórios atribuídos, "
                f"{self.stats['descriptions_generated']} descrições geradas. "
                f"Estrutura detectada: {self.stats['structure_detected']}")

# Função auxiliar para teste
def test_complex_structure_detection():
    """Função de teste para detectar estruturas complexas"""
    organizer = AIInventoryOrganizer()
    
    # Simular dados do arquivo Excel real
    test_data = {
        'Col1': [None, None, 'Anatomia', 'Esqueleto', 'Modelo de Anatomia'],
        'Col2': [None, None, None, 3, 2],
        'Col3': [None, None, None, None, None],
        'Col4': [None, None, None, None, None],
        'Col5': [None, None, 'Microbiologia', 'Materiais', 'Capela de Exaustão'],
        'Col6': [None, None, None, 'Quantidade', 1]
    }
    
    df = pd.DataFrame(test_data)
    
    print("=== TESTE DE DETECÇÃO DE ESTRUTURA ===")
    structure_info = organizer._detect_complex_structure(df)
    
    print("Estrutura detectada:")
    for col in structure_info['detected_columns']:
        print(f"  - Coluna {col['index']}: {col['name']} -> {col['type']} ({col['data_count']} itens)")
    
    materials_df = organizer._extract_materials_from_complex_structure(df, structure_info)
    
    print(f"\nMateriais extraídos: {len(materials_df)}")
    if not materials_df.empty:
        print(materials_df.to_string())
    
    return structure_info, materials_df