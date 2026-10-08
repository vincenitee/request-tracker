"""Production settings (stub, completed in Phase 7)."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Comma-separated in .env, e.g. ALLOWED_HOSTS=tracker.example.com,www.tracker.example.com
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Same-domain deployment needs no CORS; set this only if Angular is served elsewhere.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# TODO (Phase 7): enable once HTTPS is in place, then run `manage.py check --deploy`.
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
# STATIC_ROOT = BASE_DIR / "staticfiles"
# MEDIA_ROOT = BASE_DIR / "media"
