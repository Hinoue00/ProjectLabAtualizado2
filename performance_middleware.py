# performance_middleware.py
"""
Middleware de performance para compressão e otimizações
"""
import gzip
import json
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import time

class PerformanceMiddleware(MiddlewareMixin):
    """Middleware para otimizações de performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Processa request - adiciona timestamp para medir performance"""
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Processa response - aplica compressão e headers de performance"""
        
        # 1. Adicionar header de tempo de resposta
        if hasattr(request, 'start_time'):
            response_time = (time.time() - request.start_time) * 1000  # em ms
            response['X-Response-Time'] = f"{response_time:.2f}ms"
        
        # 2. Compressão GZIP para respostas grandes
        if self._should_compress(request, response):
            response = self._compress_response(response)
        
        # 3. Headers de cache para recursos estáticos
        if self._is_static_resource(request.path):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
        
        # 4. Headers de performance para páginas dinâmicas
        elif response.status_code == 200 and response.get('Content-Type', '').startswith('text/html'):
            response['Cache-Control'] = 'private, max-age=0, must-revalidate'
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
        
        # 5. Adicionar informações de debug (apenas em desenvolvimento)
        if settings.DEBUG:
            from django.db import connection
            response['X-DB-Queries'] = str(len(connection.queries))
        
        return response
    
    def _should_compress(self, request, response):
        """Verifica se deve comprimir a resposta"""
        # Não comprimir se já está comprimido
        if response.get('Content-Encoding'):
            return False
        
        # Não comprimir se cliente não suporta gzip
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept_encoding:
            return False
        
        # Comprimir apenas se conteúdo for maior que 1KB
        if len(response.content) < 1024:
            return False
        
        # Comprimir apenas tipos específicos
        content_type = response.get('Content-Type', '')
        compressible_types = [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/xml',
            'application/xml'
        ]
        
        return any(content_type.startswith(ct) for ct in compressible_types)
    
    def _compress_response(self, response):
        """Comprime a resposta usando GZIP"""
        try:
            compressed_content = gzip.compress(response.content)
            
            # Criar nova resposta com conteúdo comprimido
            new_response = HttpResponse(
                compressed_content,
                content_type=response.get('Content-Type'),
                status=response.status_code
            )
            
            # Copiar headers importantes
            for header, value in response.items():
                if header.lower() not in ['content-length', 'content-encoding']:
                    new_response[header] = value
            
            # Adicionar headers de compressão
            new_response['Content-Encoding'] = 'gzip'
            new_response['Content-Length'] = str(len(compressed_content))
            new_response['Vary'] = 'Accept-Encoding'
            
            return new_response
            
        except Exception:
            # Se falhar, retornar resposta original
            return response
    
    def _is_static_resource(self, path):
        """Verifica se é um recurso estático"""
        static_prefixes = ['/static/', '/media/', '/favicon.ico']
        return any(path.startswith(prefix) for prefix in static_prefixes)

class DatabaseOptimizationMiddleware(MiddlewareMixin):
    """Middleware para otimizações de banco de dados"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Configurações otimizadas por request"""
        from django.db import connection
        
        # Configurar timeout de query por request
        with connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = 30000")  # 30 segundos
            
            # Configurar work_mem temporariamente para queries complexas
            if request.path.startswith('/dashboard/') or request.path.startswith('/reports/'):
                cursor.execute("SET work_mem = '16MB'")
        
        return None
    
    def process_response(self, request, response):
        """Reset configurações após response"""
        from django.db import connection
        
        # Reset configurações
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET statement_timeout")
                cursor.execute("RESET work_mem")
        except:
            pass
        
        return response

class JSONResponseOptimizationMiddleware(MiddlewareMixin):
    """Middleware para otimizar respostas JSON"""
    
    def process_response(self, request, response):
        """Otimiza respostas JSON"""
        if (response.get('Content-Type', '').startswith('application/json') and
            hasattr(response, 'content')):
            
            try:
                # Parse e re-serialize para compactar JSON
                data = json.loads(response.content.decode('utf-8'))
                compact_json = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
                
                response.content = compact_json.encode('utf-8')
                response['Content-Length'] = str(len(response.content))
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        return response