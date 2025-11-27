"""
Django settings for setup project.
"""
from pathlib import Path
from celery.schedules import crontab
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- CONFIGURAÇÕES DE SEGURANÇA ---

# Carrega a SECRET_KEY da variável de ambiente. Se não encontrar, gera um erro em produção.
import sys
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    print("[WARNING] SECRET_KEY não definida! Defina a variável de ambiente SECRET_KEY.", file=sys.stderr)
    SECRET_KEY = 'unsafe-default-key'  # Evite usar em produção!

# DEBUG deve ser False em produção. O valor padrão é 'False'.
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Lê os hosts permitidos da variável de ambiente. Essencial para produção.

# Domínio padrão do Fly.io (ajuste conforme seu app)
FLY_APP_DOMAIN = os.getenv('FLY_APP_DOMAIN', 'silver-cannon-app.fly.dev')
ALLOWED_HOSTS_STR = os.getenv('ALLOWED_HOSTS', f'127.0.0.1,localhost,{FLY_APP_DOMAIN}')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',') if host.strip()]

# Adiciona automaticamente os domínios do Railway (público e privado) se existirem.
RAILWAY_HOSTNAME = os.getenv('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_HOSTNAME:
    ALLOWED_HOSTS.append(f'.{RAILWAY_HOSTNAME}')

if not ALLOWED_HOSTS:
    print("[WARNING] ALLOWED_HOSTS está vazio! Defina a variável de ambiente ALLOWED_HOSTS.", file=sys.stderr)

# Lê as origens confiáveis para CSRF da variável de ambiente.

# Garante que o domínio Fly.io está nas origens confiáveis
CSRF_TRUSTED_ORIGINS_STR = os.getenv('CSRF_TRUSTED_ORIGINS', f'https://{FLY_APP_DOMAIN}')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STR.split(',') if origin.strip()]

# --- APLICAÇÕES E MIDDLEWARE ---

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'storages',
    'formulario_professores',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'setup.urls'
WSGI_APPLICATION = 'setup.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- BANCO DE DADOS ---
# Configuração robusta que usa a DATABASE_URL do Railway.
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL não definida! Usando SQLite como fallback.", file=sys.stderr)
    DATABASE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
else:
    print(f"[INFO] Usando DATABASE_URL do Railway", file=sys.stderr)

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- CACHE (REDIS) ---
REDIS_URL = os.getenv('REDIS_URL') or 'redis://localhost:6379'
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# --- CELERY ---
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_IMPORTS = ('formulario_professores.tasks',)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'disparar_mensagens': {
        'task': 'formulario_professores.tasks.verificar_disparos',
        'schedule': crontab(minute='*'),
    },
}

# --- ARQUIVOS ESTÁTICOS E DE MÍDIA ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_ACL = None # Mais seguro, controle o acesso pelo bucket policy.

# --- OUTRAS CONFIGURAÇÕES ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-BR'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/mensagens/'
LOGOUT_REDIRECT_URL = '/login/'

# Adiciona checagens de segurança para produção quando DEBUG=False
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True