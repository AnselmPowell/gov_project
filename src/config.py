import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

IS_PRODUCTION_FRONTEND = os.environ.get('IS_PRODUCTION_FRONTEND', 'false').lower() == 'true'
IS_PRODUCTION_BACKEND = os.environ.get('IS_PRODUCTION_BACKEND', 'false').lower() == 'true'

config = {
    'DEBUG': not IS_PRODUCTION_BACKEND,
    'SECRET_KEY': os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key'),
    'ALLOWED_HOSTS': ['*'] if not IS_PRODUCTION_BACKEND else ['basedatastorev2-production.up.railway.app'],
    'CORS_ALLOWED_ORIGINS': [
        'http://localhost:3000',
        'https://baseinterfacev1-production.up.railway.app'
    ],
    'DATABASE_URL': os.environ.get('POSTGRES_URL') if IS_PRODUCTION_BACKEND else os.environ.get('POSTGRES_URL_DEV'),
    'STATIC_ROOT': BASE_DIR / 'staticfiles' if IS_PRODUCTION_BACKEND else None,
}


