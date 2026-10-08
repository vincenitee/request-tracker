"""
Base settings shared by every environment.

dev.py and prod.py import everything from here and override what differs.
See https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from datetime import timedelta
from pathlib import Path

import environ

# config/settings/base.py -> three parents up is backend/ (where manage.py and .env live).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local
    "apps.accounts",
    "apps.core",
    "apps.service_requests",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be above CommonMiddleware
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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# Custom user model. Must be set before the first migrate.
AUTH_USER_MODEL = "accounts.User"


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = "Asia/Manila"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Rates come from API_USER_THROTTLE_RATE / LOGIN_THROTTLE_RATE below (read per request).
    "DEFAULT_THROTTLE_CLASSES": ["apps.core.throttling.ApiUserRateThrottle"],
    # One error shape for the whole API: {"detail": ..., "errors": {field: [..]}}
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}


# JWT (djangorestframework-simplejwt)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# Uploaded files (attachments). Never served directly: there is no MEDIA_URL route,
# files are only reachable through the permission-checked download endpoint.
MEDIA_ROOT = BASE_DIR / "media"

# Request body limits. Non-file form/JSON data above 1 MB is refused; uploaded files above
# 2.5 MB are spooled to a temp file instead of memory. The hard cap on total upload size
# belongs in Nginx (client_max_body_size) in production.
DATA_UPLOAD_MAX_MEMORY_SIZE = 1 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = int(2.5 * 1024 * 1024)

# Attachment rules (mirrored in frontend/src/app/shared/constants/attachments.ts)
ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024
ATTACHMENT_MAX_PER_REQUEST = 5
ATTACHMENT_ALLOWED_EXTENSIONS = ("pdf", "png", "jpg", "jpeg", "docx", "xlsx")


# Throttling (429). Counters live in Django's cache: the default per-process LocMemCache is fine
# for dev; production with several workers needs a shared cache (Redis) - Phase 7.
LOGIN_THROTTLE_RATE = env("LOGIN_THROTTLE_RATE", default="10/min")  # per IP, on POST /auth/token/
API_USER_THROTTLE_RATE = env("API_USER_THROTTLE_RATE", default="1000/hour")  # per user (per IP if anonymous)


# OpenAPI (drf-spectacular). Schema and Swagger UI are served only when DEBUG is True.
SPECTACULAR_SETTINGS = {
    "TITLE": "Request Tracker API",
    "DESCRIPTION": (
        "Internal request workflow: staff submit requests, reviewers approve or reject, "
        "admins manage users, departments and categories. Authenticate with "
        "POST /api/v1/auth/token/ and send `Authorization: Bearer <access>`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,  # separate request/response components (needed for file uploads)
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    "ENUM_NAME_OVERRIDES": {
        "RequestStatusEnum": "apps.service_requests.models.Request.Status",
        "RequestPriorityEnum": "apps.service_requests.models.Request.Priority",
        "UserRoleEnum": "apps.accounts.models.User.Role",
    },
}


# Logging: one line per event in key=value form. Never log passwords, tokens or request bodies.
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "kv": {"format": 'ts=%(asctime)s level=%(levelname)s logger=%(name)s msg="%(message)s"'},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "kv"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
