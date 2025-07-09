# inventory/services.py - Versão mínima que NÃO vai dar erro
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DoclingService:
    """
    Serviço básico para análise de materiais
    Funciona sem dependências externas
    """
    
    def __init__(self):
        # Inicialização básica e segura
        self.enabled = False  # Por enquanto desabilitado
        self.nlp = None
        
        # Base de conhecimento simples
        self.category_keywords = {
            'consumable': [
                'papel', 'caneta', 'lapis', 'reagente', 'produto', 'quimico', 
                'tinta', 'cola', 'fita', 'luva', 'descartavel'
            ],
            'permanent': [
                'microscopio', 'computador', 'monitor', 'impressora', 
                'equipamento', 'aparelho', 'maquina', 'ferramenta', 'bancada'
            ],
            'perishable': [
                'medicamento', 'vacina', 'amostra', 'cultura', 'biologico', 
                'enzima', 'proteina', 'sangue'
            ]
        }
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Análise básica de texto
        Retorna resultado padrão para manter compatibilidade
        """
        if not text:
            return {
                'entities': [],
                'keywords': [],
                'confidence': 0.0
            }
        
        # Análise muito simples - extrair palavras principais
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3][:5]
        
        return {
            'entities': [],
            'keywords': keywords,
            'confidence': 0.5
        }
    
    def categorize_material(self, description: str) -> str:
        """
        Categorização básica por palavras-chave
        """
        if not description:
            return 'consumable'  # Padrão
        
        text = description.lower()
        
        # Contar pontos por categoria
        scores = {'consumable': 0, 'permanent': 0, 'perishable': 0}
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        # Retornar categoria com maior pontuação
        best_category = max(scores, key=scores.get)
        
        # Se empate, usar regras simples
        if scores[best_category] == 0:
            if any(word in text for word in ['equipamento', 'aparelho', 'computador']):
                return 'permanent'
            elif any(word in text for word in ['medicamento', 'vacina', 'biologico']):
                return 'perishable'
            else:
                return 'consumable'
        
        return best_category
    
    def generate_material_suggestions(self, partial_info: str, category_type: str = None) -> List[Dict[str, str]]:
        """
        Sugestões básicas de materiais
        """
        basic_suggestions = [
            {'name': 'Papel A4', 'description': 'Papel para impressão'},
            {'name': 'Caneta', 'description': 'Caneta para escrita'},
            {'name': 'Microscópio', 'description': 'Equipamento de laboratório'},
        ]
        
        return basic_suggestions[:3]  # Máximo 3 sugestões