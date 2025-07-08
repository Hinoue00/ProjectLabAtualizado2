"""
Configurações de desenvolvimento para o projeto LabConnect.
"""
import os
from dotenv import load_dotenv
from .base import *

load_dotenv()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-s!9v%s#j@@tjx#=82c5id%t=(w4!pxxi331rnb!n_4^21$tty1')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# # ADICIONE ESTAS LINHAS PARA DEBUG:
# print(f"DEBUG: DB_NAME='{os.environ.get('DB_NAME', '')}'")
# print(f"DEBUG: DB_USER='{os.environ.get('DB_USER', '')}'")
# print(f"DEBUG: DB_PASSWORD='{os.environ.get('DB_PASSWORD', '')}'")
# print(f"DEBUG: DB_HOST='{os.environ.get('DB_HOST', '')}'")
# print(f"DEBUG: DB_PORT='{os.environ.get('DB_PORT', '5432')}'")
# # FIM DAS LINHAS DE DEBUG

# Database para desenvolvimento
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', ''),  # Ex: labconnect_dev
        'USER': os.environ.get('DB_USER', ''),   # Ex: postgres ou um usuário específico
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),  # Ou o host onde seu PostgreSQL está rodando
        'PORT': os.environ.get('DB_PORT', '5432'),       # Porta padrão do PostgreSQL
    }
}

# Cache para desenvolvimento
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'labconnect.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'dashboard': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# Criar diretório de logs se não existir
log_dir = BASE_DIR / 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configuração para impressão de emails no console (sem envio real)
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'