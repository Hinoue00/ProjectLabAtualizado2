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

# Database para desenvolvimento
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Cache para desenvolvimento
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Configuração para impressão de emails no console (sem envio real)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'