# inventory/services.py - Docling Service Avançado para Gestão Inteligente
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.db.models import Q
import json
from collections import Counter
import unicodedata

import spacy

logger = logging.getLogger(__name__)

class DoclingService:
    """
    Serviço avançado para análise inteligente de materiais
    Combina regras linguísticas + análise semântica + machine learning básico
    """
    
    def __init__(self):
        self.enabled = True
        self.nlp = None
        
        # Tentar carregar spaCy se disponível
        try:
            import spacy
            self.nlp = spacy.load("pt_core_news_sm")
            logger.info("SpaCy carregado com sucesso")
        except (ImportError, OSError):
            logger.warning("SpaCy não disponível, usando análise baseada em regras")
        
        # Base de conhecimento avançada
        self.category_knowledge = self._build_advanced_knowledge_base()
        self.laboratory_mapping = self._build_laboratory_mapping()
        self.material_patterns = self._build_material_patterns()
        self.brand_indicators = self._build_brand_indicators()
        
    def _build_advanced_knowledge_base(self) -> Dict[str, Dict]:
        """Constrói base de conhecimento avançada por categoria"""
        return {
            'consumable': {
                'keywords': [
                    'papel', 'caneta', 'lapis', 'borracha', 'grampeador', 'clipe',
                    'reagente', 'solucao', 'acido', 'base', 'sal', 'oxido',
                    'luva', 'mascara', 'touca', 'avental', 'descartavel',
                    'seringa', 'agulha', 'gaze', 'algodao', 'bandagem',
                    'tinta', 'corante', 'cola', 'fita', 'adesivo'
                ],
                'indicators': [
                    'descartavel', 'uso unico', 'consumivel', 'ml', 'mg', 'g',
                    'litro', 'pacote', 'caixa', 'frasco', 'tubo'
                ],
                'contexts': [
                    'para experimento', 'analise', 'teste', 'medicao',
                    'escritorio', 'administrativo', 'limpeza'
                ]
            },
            'permanent': {
                'keywords': [
                    'microscopio', 'computador', 'monitor', 'impressora', 'scanner',
                    'balanca', 'estufa', 'autoclave', 'centrifuga', 'agitador',
                    'aquecedor', 'refrigerador', 'freezer', 'geladeira',
                    'bancada', 'mesa', 'cadeira', 'armario', 'estante',
                    'equipamento', 'aparelho', 'maquina', 'instrumento',
                    'projetor', 'quadro', 'lousa', 'televisao'
                ],
                'indicators': [
                    'equipamento', 'modelo', 'marca', 'serie', 'digital',
                    'eletronico', 'automatico', 'portatil', 'fixo'
                ],
                'contexts': [
                    'laboratorio', 'sala de aula', 'escritorio', 'pesquisa',
                    'ensino', 'demonstracao', 'medicao precisao'
                ]
            },
            'perishable': {
                'keywords': [
                    'medicamento', 'vacina', 'soro', 'antibiotico', 'vitamina',
                    'amostra', 'cultura', 'bacteria', 'virus', 'fungo',
                    'enzima', 'proteina', 'hormonio', 'plasma', 'sangue',
                    'biologico', 'organico', 'vivo', 'fresco'
                ],
                'indicators': [
                    'validade', 'vencimento', 'refrigeracao', 'congelamento',
                    'temperatura', 'esteril', 'contaminacao', 'prazo'
                ],
                'contexts': [
                    'biologico', 'microbiologia', 'farmacia', 'medicina',
                    'veterinaria', 'biotecnologia', 'genetica'
                ]
            }
        }
    
    def _build_laboratory_mapping(self) -> Dict[str, List[str]]:
        """Mapeia tipos de material para laboratórios específicos"""
        return {
            'informatica': [
                'computador', 'notebook', 'tablet', 'monitor', 'teclado',
                'mouse', 'impressora', 'scanner', 'projetor', 'cabo',
                'software', 'hardware', 'rede', 'internet'
            ],
            'quimica': [
                'reagente', 'acido', 'base', 'sal', 'solucao', 'composto',
                'elemento', 'molecula', 'atom', 'reacao', 'sintese',
                'analise', 'titulacao', 'ph', 'concentracao'
            ],
            'biologia': [
                'microscopio', 'lamina', 'laminula', 'corante', 'cultura',
                'bacteria', 'celula', 'tecido', 'orgao', 'organismo',
                'dna', 'rna', 'proteina', 'enzima', 'genetica'
            ],
            'fisica': [
                'metro', 'regua', 'balanca', 'peso', 'massa', 'forca',
                'energia', 'potencia', 'voltagem', 'corrente', 'resistencia',
                'capacitor', 'indutor', 'osciloscópio', 'multimetro'
            ],
            'engenharia': [
                'ferramenta', 'chave', 'parafuso', 'porca', 'martelo',
                'furadeira', 'morsa', 'alicate', 'esquadro', 'nivel',
                'trena', 'compasso', 'transferidor', 'calibrador'
            ],
            'medicina': [
                'estetoscopio', 'termometro', 'seringa', 'agulha', 'gaze',
                'curativo', 'medicamento', 'vacina', 'soro', 'plasma',
                'sangue', 'urina', 'exame', 'diagnostico'
            ]
        }
    
    def _build_material_patterns(self) -> Dict[str, str]:
        """Padrões regex para identificar tipos específicos de materiais"""
        return {
            'chemicals': r'(acido|base|hidroxido|cloreto|sulfato|nitrato|carbonato)\s+de\s+\w+',
            'electronics': r'(computador|notebook|monitor|impressora)\s+(modelo|marca)?\s*\w*',
            'measurements': r'\d+\s*(ml|mg|kg|g|l|mm|cm|m|polegada|inch)',
            'models': r'(modelo|ref|referencia|codigo)\s*:?\s*([a-zA-Z0-9\-]+)',
            'brands': r'(marca|fabricante)\s*:?\s*(\w+)',
            'temperatures': r'(-?\d+)\s*(°C|celsius|graus)',
            'concentrations': r'\d+\s*(%|ppm|molar|M|normal|N)'
        }
    
    def _build_brand_indicators(self) -> List[str]:
        """Lista de marcas conhecidas para identificação automática"""
        return [
            # Tecnologia
            'apple', 'samsung', 'dell', 'hp', 'lenovo', 'asus', 'acer',
            'canon', 'epson', 'brother', 'xerox', 'microsoft', 'logitech',
            
            # Laboratório
            'zeiss', 'olympus', 'nikon', 'leica', 'mettler', 'toledo',
            'sartorius', 'eppendorf', 'thermo', 'fisher', 'scientific',
            
            # Químicos
            'merck', 'sigma', 'aldrich', 'carlo', 'erba', 'vetec',
            'synth', 'impex', 'dinâmica', 'labsynth'
        ]
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Análise avançada de texto usando múltiplas técnicas
        """
        if not text:
            return self._empty_analysis()
        
        # Normalizar texto
        normalized_text = self._normalize_text(text)
        
        # Análise com spaCy se disponível
        nlp_analysis = self._analyze_with_spacy(text) if self.nlp else {}
        
        # Análise baseada em regras
        rule_analysis = self._analyze_with_rules(normalized_text)
        
        # Análise de padrões específicos
        pattern_analysis = self._analyze_patterns(text)
        
        # Combinar resultados
        combined_analysis = self._combine_analyses(
            nlp_analysis, rule_analysis, pattern_analysis
        )
        
        return combined_analysis
    
    def _analyze_with_spacy(self, text: str) -> Dict[str, Any]:
        """Análise usando spaCy para extração de entidades"""
        try:
            doc = self.nlp(text)
            
            entities = []
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'description': spacy.explain(ent.label_) if hasattr(spacy, 'explain') else ent.label_
                })
            
            # Extrair tokens importantes
            keywords = []
            for token in doc:
                if (not token.is_stop and not token.is_punct and 
                    len(token.text) > 2 and token.pos_ in ['NOUN', 'ADJ', 'VERB']):
                    keywords.append(token.lemma_.lower())
            
            return {
                'entities': entities,
                'keywords': list(set(keywords))[:15],
                'confidence': 0.85
            }
            
        except Exception as e:
            logger.error(f"Erro na análise spaCy: {e}")
            return {}
    
    def _analyze_with_rules(self, text: str) -> Dict[str, Any]:
        """Análise baseada em regras linguísticas"""
        words = text.split()
        
        # Extrair palavras-chave relevantes
        keywords = []
        for word in words:
            if len(word) > 2 and word not in self._get_stop_words():
                keywords.append(word)
        
        # Análise de sentimento básico
        sentiment = self._analyze_sentiment(text)
        
        # Identificar contexto
        context = self._identify_context(text)
        
        return {
            'keywords': keywords[:10],
            'sentiment': sentiment,
            'context': context,
            'confidence': 0.7
        }
    
    def _analyze_patterns(self, text: str) -> Dict[str, Any]:
        """Análise usando padrões regex específicos"""
        patterns_found = {}
        
        for pattern_name, pattern in self.material_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                patterns_found[pattern_name] = matches
        
        return {
            'patterns': patterns_found,
            'confidence': 0.6 if patterns_found else 0.3
        }
    
    def categorize_material(self, description: str, name: str = "") -> Dict[str, Any]:
        """
        Categorização inteligente avançada
        Retorna categoria + confiança + explicação
        """
        if not description and not name:
            return self._default_categorization()
        
        full_text = f"{name} {description}".strip()
        normalized_text = self._normalize_text(full_text)
        
        # Calcular scores por categoria
        category_scores = {}
        explanations = {}
        
        for category, knowledge in self.category_knowledge.items():
            score, explanation = self._calculate_category_score(
                normalized_text, knowledge
            )
            category_scores[category] = score
            explanations[category] = explanation
        
        # Determinar melhor categoria
        best_category = max(category_scores, key=category_scores.get)
        confidence = category_scores[best_category]
        
        # Aplicar regras de negócio
        final_category, final_confidence = self._apply_business_rules(
            best_category, confidence, normalized_text
        )
        
        return {
            'category': final_category,
            'confidence': final_confidence,
            'explanation': explanations[final_category],
            'all_scores': category_scores,
            'suggested_lab': self._suggest_laboratory(normalized_text)
        }
    
    def _calculate_category_score(self, text: str, knowledge: Dict) -> Tuple[float, str]:
        """Calcula score de uma categoria específica"""
        score = 0.0
        reasons = []
        
        # Score por palavras-chave
        keyword_hits = 0
        for keyword in knowledge['keywords']:
            if keyword in text:
                keyword_hits += 1
                score += 2.0
                reasons.append(f"palavra-chave: {keyword}")
        
        # Score por indicadores
        for indicator in knowledge['indicators']:
            if indicator in text:
                score += 1.5
                reasons.append(f"indicador: {indicator}")
        
        # Score por contexto
        for context in knowledge['contexts']:
            if context in text:
                score += 1.0
                reasons.append(f"contexto: {context}")
        
        # Normalizar score
        max_possible = len(knowledge['keywords']) * 2.0 + len(knowledge['indicators']) * 1.5
        normalized_score = min(score / max_possible if max_possible > 0 else 0, 1.0)
        
        explanation = f"Score: {normalized_score:.2f} - " + ", ".join(reasons[:3])
        
        return normalized_score, explanation
    
    def _apply_business_rules(self, category: str, confidence: float, text: str) -> Tuple[str, float]:
        """Aplica regras de negócio específicas"""
        
        # Regra 1: Equipamentos caros são sempre permanentes
        expensive_indicators = ['microscopio', 'computador', 'impressora', 'balanca']
        if any(indicator in text for indicator in expensive_indicators):
            return 'permanent', max(confidence, 0.8)
        
        # Regra 2: Produtos com validade são perecíveis
        perishable_indicators = ['validade', 'vencimento', 'refrigerar', 'congelar']
        if any(indicator in text for indicator in perishable_indicators):
            return 'perishable', max(confidence, 0.7)
        
        # Regra 3: Produtos com quantidade em ml/mg são consumíveis
        if re.search(r'\d+\s*(ml|mg|g)\b', text):
            return 'consumable', max(confidence, 0.6)
        
        return category, confidence
    
    def _suggest_laboratory(self, text: str) -> Optional[str]:
        """Sugere laboratório baseado no contexto do material"""
        lab_scores = {}
        
        for lab_type, keywords in self.laboratory_mapping.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                lab_scores[lab_type] = score
        
        if lab_scores:
            return max(lab_scores, key=lab_scores.get)
        
        return None
    
    def suggest_material_improvements(self, material_id: int) -> Dict[str, Any]:
        """
        Sugere melhorias para um material específico
        """
        from .models import Material
        
        try:
            material = Material.objects.get(id=material_id)
        except Material.DoesNotExist:
            return {'error': 'Material não encontrado'}
        
        suggestions = []
        
        # Analisar descrição atual
        current_analysis = self.analyze_text(material.description)
        
        # Sugestão 1: Melhorar descrição
        if len(material.description.split()) < 5:
            suggestions.append({
                'type': 'description',
                'title': 'Descrição muito curta',
                'suggestion': 'Adicione mais detalhes como marca, modelo, especificações técnicas',
                'priority': 'medium'
            })
        
        # Sugestão 2: Verificar categoria
        category_analysis = self.categorize_material(material.description, material.name)
        if category_analysis['confidence'] < 0.5:
            suggestions.append({
                'type': 'category',
                'title': 'Categoria incerta',
                'suggestion': f"Considere alterar para: {category_analysis['category']}",
                'priority': 'high'
            })
        
        # Sugestão 3: Estoque mínimo
        if material.minimum_stock < 1:
            suggestions.append({
                'type': 'stock',
                'title': 'Estoque mínimo muito baixo',
                'suggestion': 'Defina um estoque mínimo adequado para evitar faltas',
                'priority': 'medium'
            })
        
        return {
            'material': {
                'id': material.id,
                'name': material.name,
                'current_category': material.category.name
            },
            'suggestions': suggestions,
            'analysis': current_analysis,
            'recommended_category': category_analysis
        }
    
    def find_similar_materials(self, material_id: int, limit: int = 5) -> List[Dict]:
        """
        Encontra materiais similares usando análise semântica
        """
        from .models import Material
        
        try:
            target_material = Material.objects.get(id=material_id)
        except Material.DoesNotExist:
            return []
        
        # Analisar material alvo
        target_analysis = self.analyze_text(
            f"{target_material.name} {target_material.description}"
        )
        target_keywords = set(target_analysis.get('keywords', []))
        
        # Buscar materiais similares
        similar_materials = []
        other_materials = Material.objects.exclude(id=material_id).select_related('category')
        
        for material in other_materials:
            material_text = f"{material.name} {material.description}"
            material_analysis = self.analyze_text(material_text)
            material_keywords = set(material_analysis.get('keywords', []))
            
            # Calcular similaridade (Jaccard)
            intersection = len(target_keywords & material_keywords)
            union = len(target_keywords | material_keywords)
            similarity = intersection / union if union > 0 else 0
            
            if similarity > 0.2:  # Limiar de similaridade
                similar_materials.append({
                    'material': material,
                    'similarity': similarity,
                    'common_keywords': list(target_keywords & material_keywords)
                })
        
        # Ordenar por similaridade
        similar_materials.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_materials[:limit]
    
    def generate_inventory_insights(self) -> Dict[str, Any]:
        """
        Gera insights avançados sobre o inventário
        """
        from .models import Material, MaterialCategory
        
        insights = {
            'category_distribution': {},
            'description_quality': {},
            'suggested_improvements': [],
            'anomalies': [],
            'trends': {}
        }
        
        materials = Material.objects.all().select_related('category')
        
        # Análise de distribuição por categoria
        category_counts = Counter()
        quality_scores = []
        
        for material in materials:
            category_counts[material.category.material_type] += 1
            
            # Avaliar qualidade da descrição
            desc_analysis = self.analyze_text(material.description)
            quality_score = len(desc_analysis.get('keywords', [])) / 10.0
            quality_scores.append(quality_score)
            
            # Detectar anomalias
            category_analysis = self.categorize_material(
                material.description, material.name
            )
            
            if (category_analysis['confidence'] > 0.7 and 
                category_analysis['category'] != material.category.material_type):
                insights['anomalies'].append({
                    'material_id': material.id,
                    'material_name': material.name,
                    'current_category': material.category.material_type,
                    'suggested_category': category_analysis['category'],
                    'confidence': category_analysis['confidence']
                })
        
        insights['category_distribution'] = dict(category_counts)
        insights['description_quality'] = {
            'average_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'low_quality_count': sum(1 for score in quality_scores if score < 0.3)
        }
        
        return insights
    
    # Métodos auxiliares
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para análise"""
        # Remover acentos
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Converter para minúsculas e limpar
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _get_stop_words(self) -> set:
        """Lista de stop words em português"""
        return {
            'de', 'da', 'do', 'das', 'dos', 'para', 'com', 'sem', 'por',
            'em', 'na', 'no', 'nas', 'nos', 'a', 'o', 'as', 'os', 'um',
            'uma', 'uns', 'umas', 'e', 'ou', 'mas', 'que', 'como', 'quando',
            'onde', 'porque', 'se', 'isso', 'esse', 'essa', 'este', 'esta'
        }
    
    def _analyze_sentiment(self, text: str) -> str:
        """Análise básica de sentimento"""
        positive_words = ['bom', 'otimo', 'excelente', 'qualidade', 'eficiente']
        negative_words = ['ruim', 'quebrado', 'defeito', 'problema', 'vencido']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _identify_context(self, text: str) -> List[str]:
        """Identifica contexto do material"""
        contexts = []
        
        context_mapping = {
            'laboratorio': ['experimento', 'analise', 'teste', 'pesquisa'],
            'escritorio': ['administrativo', 'documentacao', 'impressao'],
            'ensino': ['aula', 'demonstracao', 'educacao', 'aluno'],
            'manutencao': ['reparo', 'limpeza', 'conservacao']
        }
        
        text_lower = text.lower()
        for context, keywords in context_mapping.items():
            if any(keyword in text_lower for keyword in keywords):
                contexts.append(context)
        
        return contexts
    
    def _combine_analyses(self, *analyses) -> Dict[str, Any]:
        """Combina resultados de múltiplas análises"""
        combined = {
            'keywords': [],
            'entities': [],
            'confidence': 0.0,
            'patterns': {},
            'sentiment': 'neutral',
            'context': []
        }
        
        confidences = []
        
        for analysis in analyses:
            if not analysis:
                continue
                
            # Combinar keywords
            combined['keywords'].extend(analysis.get('keywords', []))
            
            # Combinar entidades
            combined['entities'].extend(analysis.get('entities', []))
            
            # Combinar padrões
            combined['patterns'].update(analysis.get('patterns', {}))
            
            # Coletar confiança
            if 'confidence' in analysis:
                confidences.append(analysis['confidence'])
            
            # Outros campos
            if 'sentiment' in analysis:
                combined['sentiment'] = analysis['sentiment']
            if 'context' in analysis:
                combined['context'].extend(analysis['context'])
        
        # Remover duplicatas
        combined['keywords'] = list(set(combined['keywords']))[:15]
        combined['context'] = list(set(combined['context']))
        
        # Calcular confiança média
        combined['confidence'] = sum(confidences) / len(confidences) if confidences else 0.5
        
        return combined
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Retorna análise vazia"""
        return {
            'keywords': [],
            'entities': [],
            'confidence': 0.0,
            'patterns': {},
            'sentiment': 'neutral',
            'context': []
        }
    
    def _default_categorization(self) -> Dict[str, Any]:
        """Retorna categorização padrão"""
        return {
            'category': 'consumable',
            'confidence': 0.3,
            'explanation': 'Categoria padrão - informações insuficientes',
            'all_scores': {'consumable': 0.3, 'permanent': 0.0, 'perishable': 0.0},
            'suggested_lab': None
        }