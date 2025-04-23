import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class WhatsAppUnofficialService:
    """Classe para gerenciar serviços de mensagem WhatsApp usando WA-Automate"""
    
    @staticmethod
    def _format_phone_number(phone_number):
        """Formatar número de telefone para WhatsApp"""
        # Remover caracteres não numéricos
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Se número brasileiro e sem código do país, adicionar 55
        if len(digits_only) == 11 and not digits_only.startswith('55'):
            return f"55{digits_only}"
        # Se já tem código do país, retornar apenas dígitos
        else:
            return digits_only
    
    @staticmethod
    def send_message(to_number, message_body):
        """
        Enviar uma mensagem WhatsApp usando o serviço WA-Automate
        
        Args:
            to_number: Número do destinatário
            message_body: Conteúdo da mensagem
            
        Returns:
            bool: Status de sucesso
        """
        try:
            # Formatar número para WhatsApp
            formatted_number = WhatsAppUnofficialService._format_phone_number(to_number)
            
            # URL do servidor WA-Automate
            api_url = settings.WHATSAPP_UNOFFICIAL_API_URL
            
            # Preparar dados para envio
            data = {
                "phoneNumber": formatted_number,
                "message": message_body
            }
            
            # Enviar requisição para o servidor
            response = requests.post(f"{api_url}/send-message", json=data)
            
            # Verificar se a mensagem foi enviada com sucesso
            if response.status_code == 200 and response.json().get('success', False):
                logger.info(f"WhatsApp message sent to {formatted_number}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    # Adicione aqui os métodos para as diferentes notificações (registro, aprovação, etc.)
    # semelhantes aos que você tinha na implementação da API oficial