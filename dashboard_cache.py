# dashboard_cache.py
"""
Sistema de cache avançado para dashboard com invalidação inteligente
"""
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from functools import wraps
import hashlib
import json

class SmartDashboardCache:
    """Cache inteligente para dashboard com invalidação baseada em contexto"""
    
    CACHE_TTL = {
        'technician_dashboard': 300,  # 5 minutos
        'professor_dashboard': 600,   # 10 minutos
        'dashboard_stats': 180,       # 3 minutos
        'calendar_data': 240,         # 4 minutos
    }
    
    @classmethod
    def get_cache_key(cls, user, view_type, **kwargs):
        """Gera chave única baseada no usuário e contexto"""
        key_data = {
            'user_id': user.id,
            'user_type': user.user_type,
            'view_type': view_type,
            'department': kwargs.get('department', 'all'),
            'week_offset': kwargs.get('week_offset', 0),
            'lab_department': getattr(user, 'lab_department', None),
        }
        
        # Criar hash MD5 da chave para garantir tamanho consistente
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"dashboard_{view_type}_{key_hash}"
    
    @classmethod
    def get_cached_response(cls, user, view_type, **kwargs):
        """Obtém resposta cacheada se disponível"""
        cache_key = cls.get_cache_key(user, view_type, **kwargs)
        return cache.get(cache_key)
    
    @classmethod
    def cache_response(cls, user, view_type, response_data, **kwargs):
        """Cacheia resposta do dashboard"""
        cache_key = cls.get_cache_key(user, view_type, **kwargs)
        ttl = cls.CACHE_TTL.get(view_type, 300)
        
        cache.set(cache_key, response_data, ttl)
        return cache_key
    
    @classmethod
    def invalidate_user_cache(cls, user_id=None, user_type=None, department=None):
        """Invalida cache específico do usuário ou tipo"""
        patterns = []
        
        if user_id:
            patterns.append(f"dashboard_*_*{user_id}*")
        
        if user_type:
            patterns.append(f"dashboard_{user_type}_*")
        
        if department:
            patterns.append(f"dashboard_*_*{department}*")
        
        # Para Redis, usar delete_pattern
        for pattern in patterns:
            try:
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern(pattern)
            except:
                pass

def smart_cache_dashboard(view_type):
    """Decorator para cache inteligente de dashboard"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Extrair parâmetros para cache
            cache_params = {
                'department': request.GET.get('department', 'all'),
                'week_offset': request.GET.get('week_offset', 0),
            }
            
            # Verificar se é request AJAX (não cachear)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return view_func(request, *args, **kwargs)
            
            # Tentar obter do cache
            cached_response = SmartDashboardCache.get_cached_response(
                request.user, view_type, **cache_params
            )
            
            if cached_response:
                # Retornar resposta cacheada
                from django.http import HttpResponse
                response = HttpResponse(cached_response['content'])
                response['Content-Type'] = cached_response.get('content_type', 'text/html')
                response['X-Cache'] = 'HIT'
                return response
            
            # Executar view original
            response = view_func(request, *args, **kwargs)
            
            # Cachear apenas respostas bem-sucedidas HTML
            if (response.status_code == 200 and 
                response.get('Content-Type', '').startswith('text/html')):
                
                cache_data = {
                    'content': response.content.decode('utf-8'),
                    'content_type': response.get('Content-Type'),
                }
                
                SmartDashboardCache.cache_response(
                    request.user, view_type, cache_data, **cache_params
                )
                response['X-Cache'] = 'MISS'
            
            return response
        return wrapper
    return decorator

# Middleware para cache de fragmentos
class DashboardFragmentCacheMiddleware:
    """Middleware para cache de fragmentos específicos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Processar request
        response = self.get_response(request)
        
        # Adicionar headers de cache para recursos estáticos
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 ano
            response['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
        
        # Headers para pages de dashboard
        elif '/dashboard/' in request.path and response.status_code == 200:
            response['Cache-Control'] = 'private, max-age=300'  # 5 minutos
            response['Vary'] = 'User-Agent, Accept-Encoding'
        
        return response

# Template tags para cache de fragmentos
from django import template
from django.core.cache import cache
from django.template.loader import render_to_string

register = template.Library()

@register.inclusion_tag('dashboard/fragments/stats_card.html', takes_context=True)
def cached_stats_card(context, stats_type, refresh_interval=300):
    """Template tag para cache de cards de estatísticas"""
    user = context['request'].user
    cache_key = f"stats_card_{stats_type}_{user.id}_{user.user_type}"
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Gerar dados baseado no tipo
    if stats_type == 'pending_appointments':
        from scheduling.models import ScheduleRequest
        count = ScheduleRequest.objects.filter(status='pending').count()
        data = {
            'title': 'Agendamentos Pendentes',
            'count': count,
            'icon': 'clock',
            'color': 'warning' if count > 10 else 'info'
        }
    
    elif stats_type == 'materials_alert':
        from inventory.models import Material
        from django.db.models import F
        count = Material.objects.filter(quantity__lt=F('minimum_stock')).count()
        data = {
            'title': 'Materiais em Alerta',
            'count': count,
            'icon': 'exclamation-triangle',
            'color': 'danger' if count > 5 else 'warning'
        }
    
    else:
        data = {'title': 'Estatística', 'count': 0, 'icon': 'info', 'color': 'secondary'}
    
    # Cachear resultado
    cache.set(cache_key, data, refresh_interval)
    return data

@register.simple_tag(takes_context=True)
def cache_fragment(context, fragment_name, timeout=300):
    """Tag para cache de fragmentos HTML"""
    user = context['request'].user
    cache_key = f"fragment_{fragment_name}_{user.id}"
    
    content = cache.get(cache_key)
    if content:
        return content
    
    # Se não está em cache, retornar marcador para renderização
    return f"<!-- CACHE_FRAGMENT:{fragment_name}:{timeout} -->"