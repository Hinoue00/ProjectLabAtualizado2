# inventory/services.py
import logging
import docling
from django.conf import settings

class DoclingService:
    def __init__(self):
            try:
                # Check if Docling is enabled and model path is set
                if getattr(settings, 'DOCLING_ENABLED', False):
                    docling_model_path = getattr(settings, 'DOCLING_MODEL', None)
                    
                    if not docling_model_path:
                        raise ValueError("DOCLING_MODEL path is not configured in settings")
                    
                    # Safely load the Docling model
                    self.nlp = docling.load(docling_model_path)
                else:
                    self.nlp = None
            except ImportError:
                print("Docling library is not installed")
                self.nlp = None
            except Exception as e:
                print(f"Error initializing Docling service: {e}")
                self.nlp = None

    def process(self, text):
            if self.nlp:
                # Add your Docling processing logic here
                return self.nlp.process(text)
            else:
                print("Docling service is not initialized")
                return None
    
    # inventory/services.py
    def analyze_text(self, text):
        try:
            """Analisa um texto e retorna entidades e palavras-chave"""
            if self.nlp is None:
            # Retornar um resultado padrão quando nlp não estiver disponível
                return {
                    "entities": [],
                    "keywords": [],
                    "summary": "Análise não disponível"
                }
        
            doc = self.nlp(text)
            
            # Extrair entidades
            entities = [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                }
                for ent in doc.ents
            ]
            
            # Extrair palavras-chave (tokens importantes)
            keywords = [
                token.text for token in doc 
                if not token.is_stop and not token.is_punct and token.pos_ in ["NOUN", "PROPN", "ADJ"]
            ]
            
            return {
                "entities": entities,
                "keywords": keywords,
                "summary": " ".join(keywords[:5])  # Uma versão resumida simples
            }
        except Exception as e:
            logging.error(f"Erro ao analisar texto com Docling: {str(e)}")
            return {
                "entities": [],
                "keywords": [],
                "summary": "Erro na análise"
        }
        
    def categorize_material(self, description):
        """Sugere categorias para materiais baseado na descrição"""
        doc = self.nlp(description.lower())
        
        # Dicionário de palavras-chave por categoria
        category_keywords = {
            "consumable": ["consumível", "descartável", "papel", "caneta", "reagente"],
            "permanent": ["permanente", "equipamento", "máquina", "ferramenta", "instrumento"],
            "perishable": ["perecível", "químico", "biológico", "vencimento", "prazo"]
        }
        
        # Calcular a pontuação para cada categoria
        scores = {category: 0 for category in category_keywords}
        
        for token in doc:
            if token.is_stop or token.is_punct:
                continue
            
            for category, keywords in category_keywords.items():
                if any(keyword in token.text or token.text in keyword for keyword in keywords):
                    scores[category] += 1
        
        # Retornar a categoria com maior pontuação
        if max(scores.values()) > 0:
            suggested_category = max(scores.items(), key=lambda x: x[1])[0]
        else:
            suggested_category = "consumable"  # Padrão se não conseguir determinar
            
        return suggested_category
    
    def generate_material_suggestions(self, partial_info, category_type=None):
        """Gera sugestões para nomes e descrições de materiais"""
        doc = self.nlp(partial_info)
        
        # Extrair características importantes
        key_terms = [token.text for token in doc if not token.is_stop and not token.is_punct]
        
        # Base de sugestões por tipo de categoria
        suggestions_by_category = {
            "consumable": [
                {"name": "Papel sulfite", "description": "Papel branco para impressão, tamanho A4, pacote com 500 folhas."},
                {"name": "Caneta esferográfica", "description": "Caneta de tinta azul, ponta média, caixa com 50 unidades."},
                {"name": "Reagente químico", "description": "Solução para experimentos laboratoriais, alta pureza."}
            ],
            "permanent": [
                {"name": "Microscópio óptico", "description": "Equipamento para visualização de amostras com ampliação de até 1000x."},
                {"name": "Balança de precisão", "description": "Balança digital com precisão de 0,001g para pesagem de materiais."},
                {"name": "Computador desktop", "description": "Computador com processador i5, 8GB RAM, HD 1TB para uso em laboratório."}
            ],
            "perishable": [
                {"name": "Cultura bacteriana", "description": "Cultura para experimentos microbiológicos, armazenar refrigerado."},
                {"name": "Reagente orgânico", "description": "Composto para análises químicas, validade de 6 meses após abertura."},
                {"name": "Solução tampão", "description": "Solução para calibração de equipamentos, validade de 3 meses."}
            ]
        }
        
        # Se não tiver categoria, usar uma mistura
        if not category_type:
            all_suggestions = []
            for suggestions in suggestions_by_category.values():
                all_suggestions.extend(suggestions)
            base_suggestions = all_suggestions
        else:
            base_suggestions = suggestions_by_category.get(category_type, [])
        
        # Personalizar as sugestões com base nas palavras-chave
        result = []
        for suggestion in base_suggestions:
            for term in key_terms:
                if term.lower() in suggestion["name"].lower() or term.lower() in suggestion["description"].lower():
                    result.append(suggestion)
                    break
        
        # Se não houver correspondências, retornar as sugestões padrão
        if not result:
            result = base_suggestions[:3]
        
        return result[:3]  # Retornar até 3 sugestões