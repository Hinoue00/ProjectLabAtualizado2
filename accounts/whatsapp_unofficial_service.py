# accounts/whatsapp_unofficial_service.py
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class WhatsAppUnofficialService:
    """Classe para gerenciar serviços de mensagem WhatsApp usando WA-Automate"""
    
    @staticmethod
    def _format_phone_number(phone_number):
        """Formatar número de telefone para WhatsApp"""
        # Verificar se o número existe
        if not phone_number:
            logger.error("Número de telefone não fornecido")
            return None
            
        # Converter para string caso não seja
        phone_str = str(phone_number)
        
        # Remover caracteres não numéricos
        digits_only = ''.join(filter(str.isdigit, phone_str))
        
        # Log para debug
        logger.info(f"Número original: {phone_number}, dígitos extraídos: {digits_only}, comprimento: {len(digits_only)}")
        
        # Casos diferentes com base no comprimento
        if len(digits_only) == 10:  # Número corporativo (DDD + 8 dígitos)
            return f"55{digits_only}"
        elif len(digits_only) == 11:  # Celular pessoal (DDD + 9 dígitos)
            return f"55{digits_only}" if not digits_only.startswith('55') else digits_only
        elif len(digits_only) == 12 and digits_only.startswith('55'):  # Já tem código país
            return digits_only
        elif len(digits_only) == 13 and digits_only.startswith('550'):  # Algumas operadoras adicionam 0
            return digits_only[0:2] + digits_only[3:]  # Remove o 0 depois do 55
        else:
            # Qualquer outro formato, tenta adicionar 55 se não começa com ele
            return f"55{digits_only}" if not digits_only.startswith('55') else digits_only
        
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
        logger.info(f"Tentando enviar WhatsApp. WHATSAPP_UNOFFICIAL_API_URL={settings.WHATSAPP_UNOFFICIAL_API_URL}, USE_WHATSAPP_NOTIFICATIONS={settings.USE_WHATSAPP_NOTIFICATIONS}")
        logger.info(f"Número original: {to_number}")


        try:
            # Formatar número para WhatsApp
            formatted_number = WhatsAppUnofficialService._format_phone_number(to_number)

            logger.info(f"Número formatado: {formatted_number}")
            
            # URL do servidor WA-Automate
            api_url = settings.WHATSAPP_UNOFFICIAL_API_URL
            
            # Log para debug
            logger.info(f"Enviando mensagem WhatsApp para {formatted_number} via {api_url}/send-message")
            
            # Preparar dados para envio
            data = {
                "phoneNumber": formatted_number,
                "message": message_body
            }
            
            # Enviar requisição para o servidor
            response = requests.post(f"{api_url}/send-message", json=data)
            
            # Log da resposta para debug
            logger.info(f"Resposta do servidor WhatsApp: {response.status_code} - {response.text}")
            
            # Verificar se a mensagem foi enviada com sucesso
            if response.status_code == 200 and response.json().get('success', False):
                logger.info(f"Mensagem WhatsApp enviada com sucesso para {formatted_number}")
                return True
            else:
                logger.error(f"Falha ao enviar mensagem WhatsApp: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem WhatsApp: {str(e)}")
            return False