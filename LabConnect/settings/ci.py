"""
Configurações específicas para CI/CD (GitHub Actions)
"""
import os
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ci-test-secret-key-for-github-actions-only-not-for-production-use'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Database para CI - usar PostgreSQL como em produção
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_labconnect',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Cache simples para CI
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ci-cache',
    }
}

# Configurações de email para testes
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Logs mínimos para CI
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# Desabilitar funcionalidades que requerem dependências pesadas
DOCLING_ENABLED = False
WHATSAPP_ENABLED = False

# Configurações específicas para testes
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Mais rápido para testes
]

# Desabilitar migrações desnecessárias em testes
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

# Para testes muito rápidos, pode descomentar:
# MIGRATION_MODULES = DisableMigrations()

# Configurações de mídia para CI
MEDIA_ROOT = '/tmp/ci_media'
STATIC_ROOT = '/tmp/ci_static'