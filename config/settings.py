"""
Configuración de InvenShop.

Las credenciales y todo lo que cambia entre máquinas se lee del archivo .env
(ver .env.example). El .env no se sube al repositorio.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(nombre, por_defecto=False):
    return os.getenv(nombre, str(por_defecto)).strip().lower() in ('1', 'true', 'si', 'sí', 'yes')


def env_lista(nombre, por_defecto=''):
    return [valor.strip() for valor in os.getenv(nombre, por_defecto).split(',') if valor.strip()]


SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('Falta SECRET_KEY en el archivo .env (copiar .env.example como .env).')

# Con DEBUG=False Django no muestra el detalle de los errores (usa las plantillas 403/404/500)
DEBUG = env_bool('DEBUG')

ALLOWED_HOSTS = env_lista('ALLOWED_HOSTS', '127.0.0.1,localhost')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'usuarios.apps.UsuariosConfig',
    'catalogo.apps.CatalogoConfig',
    'carrito.apps.CarritoConfig',
    'pedidos.apps.PedidosConfig',
    'panel.apps.PanelConfig',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'carrito.context_processors.carrito',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv('SQLITE_NOMBRE', 'db.sqlite3'),
    }
}


# Usuario propio: se inicia sesión con el email
AUTH_USER_MODEL = 'usuarios.Usuario'

LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'usuarios:inicio_segun_rol'
LOGOUT_REDIRECT_URL = 'catalogo:lista'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Imágenes de los productos
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# El carrito vive en la sesión (no se guarda en la base hasta confirmar el pedido)
CARRITO_SESSION_ID = 'carrito'

# Clases de Bootstrap para los mensajes de django.contrib.messages
from django.contrib.messages import constants as mensajes  # noqa: E402

MESSAGE_TAGS = {
    mensajes.DEBUG: 'secondary',
    mensajes.INFO: 'info',
    mensajes.SUCCESS: 'success',
    mensajes.WARNING: 'warning',
    mensajes.ERROR: 'danger',
}


# Seguridad de cookies (en producción, con HTTPS, poner SEGURO_HTTPS=True en el .env)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = env_bool('SEGURO_HTTPS')
SESSION_COOKIE_SECURE = env_bool('SEGURO_HTTPS')
X_FRAME_OPTIONS = 'DENY'


MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
