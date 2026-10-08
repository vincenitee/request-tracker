"""Local development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Angular dev server. No trailing slash.
CORS_ALLOWED_ORIGINS = ["http://localhost:4200"]
