# accounts/backends.py
import msal
import requests
import json
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

class MicrosoftGraphEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.fail_silently = fail_silently
        
    def send_messages(self, email_messages):
        """Envia mensagens de email via Microsoft Graph API"""
        if not email_messages:
            return 0
            
        # Configurações
        client_id = settings.MS_CLIENT_ID
        client_secret = settings.MS_CLIENT_SECRET
        tenant_id = settings.MS_TENANT_ID
        sender_email = settings.MS_SENDER_EMAIL
            
        # Obter token
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        
        # Solicitar token para enviar emails
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" not in result:
            error = result.get("error")
            error_description = result.get("error_description")
            if not self.fail_silently:
                raise Exception(f"Erro ao obter token: {error} - {error_description}")
            return 0
            
        access_token = result["access_token"]
        
        # Enviar cada mensagem
        sent_count = 0
        
        for message in email_messages:
            try:
                # Converter para formato Graph API
                graph_message = self._build_graph_message(message)
                
                # Enviar via Graph API
                response = requests.post(
                    f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    data=json.dumps(graph_message)
                )
                
                if response.status_code == 202:
                    sent_count += 1
                else:
                    if not self.fail_silently:
                        response_json = response.json()
                        error_msg = response_json.get('error', {}).get('message', 'Unknown error')
                        raise Exception(f"Erro ao enviar email: {error_msg}")
            except Exception as e:
                if not self.fail_silently:
                    raise
        
        return sent_count
    
    def _build_graph_message(self, email_message):
        """Converte EmailMessage do Django para formato Graph API"""
        to_recipients = [{"emailAddress": {"address": email}} for email in email_message.to]
        cc_recipients = [{"emailAddress": {"address": email}} for email in getattr(email_message, 'cc', []) or []]
        bcc_recipients = [{"emailAddress": {"address": email}} for email in getattr(email_message, 'bcc', []) or []]
        
        # Corpo da mensagem
        body = {"contentType": "HTML" if hasattr(email_message, 'content_subtype') and email_message.content_subtype == "html" else "Text", 
                "content": email_message.body}
        
        # Mensagem no formato Graph API
        graph_message = {
            "message": {
                "subject": email_message.subject,
                "body": body,
                "toRecipients": to_recipients
            },
            "saveToSentItems": "true"
        }
        
        if cc_recipients:
            graph_message["message"]["ccRecipients"] = cc_recipients
        if bcc_recipients:
            graph_message["message"]["bccRecipients"] = bcc_recipients
            
        return graph_message