from django import template
from django.conf import settings
from django.urls import reverse
import os

register = template.Library()

@register.simple_tag
def secure_file_url(file_field):
    """
    Gera URL segura para arquivos, usando view personalizada ao invés de acesso direto
    """
    if not file_field:
        return ""
    
    # Obter apenas o nome do arquivo (sem o caminho completo)
    filename = os.path.basename(file_field.name)
    
    # Gerar URL usando a view segura
    return reverse('serve_guide_file', kwargs={'file_path': filename})

@register.filter
def basename(value):
    """
    Filtra para obter apenas o nome do arquivo sem o caminho
    """
    if not value:
        return ""
    return os.path.basename(str(value))