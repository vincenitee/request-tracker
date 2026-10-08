"""Local development settings."""

import sys

from .base import *  # noqa: F401,F403
from .base import LOGGING

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Angular dev server. No trailing slash.
CORS_ALLOWED_ORIGINS = ["http://localhost:4200"]

# Keep `manage.py test` output readable: only warnings and errors from our apps while testing.
if "test" in sys.argv:
    LOGGING["loggers"]["apps"]["level"] = "WARNING"
