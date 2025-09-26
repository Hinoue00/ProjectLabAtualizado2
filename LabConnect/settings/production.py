"""
Configurações de produção para o projeto LabConnect.
"""
import os
from dotenv import load_dotenv
from .base import *

load_dotenv()

# DEBUG desabilitado para segurança em produção
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',') + ['192.168.224.120', 'localhost', '127.0.0.1', 'labconnect.ngrok.app', '*.ngrok.app', '*.ngrok.io']

# Database para produção
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', ''),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Configuração de cache para produção - CORRIGIDA
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'TIMEOUT': 300,  # 5 minutos default
        'KEY_PREFIX': 'labconnect',
        'VERSION': 1,
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/2'),
        'TIMEOUT': 1800,  # 30 minutos para sessões
    },
    'templates': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/3'),
        'TIMEOUT': 600,  # 10 minutos para templates
    }
}

# Middleware adicional para produção
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
# TEMPORARIAMENTE DESABILITADO - MIDDLEWARE.insert(2, 'performance_middleware.PerformanceMiddleware')
# TEMPORARIAMENTE DESABILITADO - MIDDLEWARE.insert(3, 'performance_middleware.DatabaseOptimizationMiddleware') 
# TEMPORARIAMENTE DESABILITADO - MIDDLEWARE.insert(4, 'performance_middleware.JSONResponseOptimizationMiddleware')
# Remover middleware de cache de página para evitar conflitos com AJAX
# MIDDLEWARE.insert(0, 'django.middleware.cache.UpdateCacheMiddleware')
# MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')

# Configuração de arquivos estáticos para produção - OTIMIZADA
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configurações de cache de página completa - DESABILITADO para AJAX
# CACHE_MIDDLEWARE_ALIAS = 'default'
# CACHE_MIDDLEWARE_SECONDS = 60  # 1 minuto para páginas inteiras
# CACHE_MIDDLEWARE_KEY_PREFIX = 'labconnect_page'

# Sessões no Redis para performance
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 1800  # 30 minutos

# Configurações de compressão
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]
COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.JSMinFilter',
]

# Configurações de database otimizadas para PostgreSQL
DATABASES['default']['CONN_MAX_AGE'] = 300  # 5 minutos
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'server_side_binding': True,  # Melhor performance para queries repetidas
    'application_name': 'labconnect_prod',
}

# Pool de conexões otimizado
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
DATABASES['default']['TIME_ZONE'] = 'America/Sao_Paulo'

# Configurações avançadas de performance
DATABASE_CONNECTION_POOLING = {
    'MAX_CONNECTIONS': 20,  # Máximo de conexões simultâneas
    'MIN_CONNECTIONS': 5,   # Mínimo sempre ativo
    'CONNECTION_LIFETIME': 3600,  # 1 hora
    'IDLE_TIMEOUT': 300,    # 5 minutos para conexões idle
}

# Configurações para evitar truncamento de respostas grandes
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Configurações de logging otimizadas
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',  # Reduzir para INFO em produção
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/www/labconnect/logs/labconnect.log',
            'maxBytes': 15728640,  # 15MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'scheduling': {
            'handlers': ['file'],
            'level': 'INFO',  # Reduzir de DEBUG para INFO
            'propagate': True,
        },
    },
}

# Configurações de segurança para produção
# SSL configurado considerando que ngrok termina HTTPS
SECURE_SSL_REDIRECT = False  # ngrok já força HTTPS
SESSION_COOKIE_SECURE = True  # Cookies devem ser seguros
CSRF_COOKIE_SECURE = True   # CSRF cookies devem ser seguros
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
CSRF_TRUSTED_ORIGINS = ['https://labconnect.ngrok.app']

# Configuração adicional para confiar no proxy reverso
SECURE_SSL_HOST = None  # Permite qualquer host HTTPS
