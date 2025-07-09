"""
Configurações base para o projeto LabConnect.
Contém configurações compartilhadas por todos os ambientes.
"""
import os
from django.contrib.messages import constants as messages
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / '.env')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',

    # Local apps
    'accounts.apps.AccountsConfig',
    'laboratories.apps.LaboratoriesConfig',
    'inventory.apps.InventoryConfig',
    'scheduling.apps.SchedulingConfig',
    'dashboard.apps.DashboardConfig',
    'reports.apps.ReportsConfig',
    'api.apps.ApiConfig',
    'whatsapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'LabConnect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.sidebar_context',
            ],
        },
    },
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Logging para automação
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'inventory_automation.log'),
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'inventory.automation_service': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'inventory.services': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'staticfiles'),
]
# Para produção
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_collected')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Authentication settings
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_redirect'
LOGOUT_REDIRECT_URL = 'login'

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Message tags
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# Sites Framework
SITE_ID = 1

# WhatsApp configuration
WHATSAPP_ENABLED = os.environ.get('WHATSAPP_ENABLED', 'True') == 'True'
WHATSAPP_SERVICE_URL = os.environ.get('WHATSAPP_SERVICE_URL', 'http://localhost:3000/api')
WHATSAPP_API_KEY = os.environ.get('WHATSAPP_API_KEY', '')

# Ollama configuration
OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434/api/chat')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')

# Configurações do Docling para automação de inventário
DOCLING_ENABLED = os.environ.get('DOCLING_ENABLED', 'True') == 'True'
DOCLING_MODEL = os.environ.get('DOCLING_MODEL', "pt_core_news_sm")
DOCLING_CACHE_DIR = os.path.join(BASE_DIR, 'docling_cache')

# Configurações de automação de inventário
INVENTORY_AUTOMATION = {
    'ENABLED': os.environ.get('INVENTORY_AUTOMATION_ENABLED', 'True') == 'True',
    'AUTO_CATEGORIZE': os.environ.get('AUTO_CATEGORIZE_MATERIALS', 'True') == 'True',
    'AUTO_ASSIGN_LAB': os.environ.get('AUTO_ASSIGN_LABORATORY', 'True') == 'True',
    'BATCH_SIZE': int(os.environ.get('AUTOMATION_BATCH_SIZE', '100')),
    'MAX_FILE_SIZE': int(os.environ.get('MAX_IMPORT_FILE_SIZE', '10485760')),  # 10MB
}

# Configurações de upload de arquivos
FILE_UPLOAD_MAX_MEMORY_SIZE = INVENTORY_AUTOMATION['MAX_FILE_SIZE']
DATA_UPLOAD_MAX_MEMORY_SIZE = INVENTORY_AUTOMATION['MAX_FILE_SIZE']

# Scheduling configuration
ALLOW_SCHEDULING_ANY_DAY = os.environ.get('ALLOW_SCHEDULING_ANY_DAY', 'True') == 'True'

