# whatsapp/client.py
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Cliente simples para enviar mensagens WhatsApp"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'WHATSAPP_SERVICE_URL', 'http://localhost:3000/api')
        self.api_key = getattr(settings, 'WHATSAPP_API_KEY', '')

    def _format_phone(self, phone):
        """
        Formata um número de telefone para o padrão WhatsApp brasileiro
        
        Args:
            phone (str): Número de telefone (com ou sem formatação)
            
        Returns:
            str: Número formatado
        """
        # Remover caracteres não numéricos
        cleaned = ''.join(filter(str.isdigit, phone))
        
        # Adicionar código do país se necessário
        if not cleaned.startswith('55'):
            cleaned = '55' + cleaned
        
        # Verificar se é um celular brasileiro com o 9 na frente
        # Formato: 55 + DDD(2) + 9 + número(8) = 13 dígitos
        if len(cleaned) == 13 and cleaned.startswith('55'):
            # Extrair o DDD (posições 2 e 3)
            ddd = cleaned[2:4]
            
            # Verificar se o quinto dígito é 9
            if cleaned[4] == '9':
                # Remover o dígito 9 inicial
                cleaned = '55' + ddd + cleaned[5:]
                logging.info(f"Número formatado: {phone} → {cleaned}")
        
        return cleaned
    
    def send_message(self, phone, message):
        """
        Envia uma mensagem WhatsApp
        
        Args:
            phone (str): Número do destinatário
            message (str): Conteúdo da mensagem
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        url = f"{self.base_url}/send-message"
        
        # Formatar número de telefone (verificar formato brasileiro)
        formatted_phone = self._format_phone(phone)
        
        # Headers com a API Key
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key
        }
        
        # Dados da requisição
        payload = {
            'phone': formatted_phone,
            'message': message
        }
        
        try:
            logger.info(f"Enviando mensagem WhatsApp para {formatted_phone}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Mensagem WhatsApp enviada com sucesso")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem WhatsApp: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao enviar mensagem WhatsApp: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar mensagem WhatsApp: {e}")
            return False