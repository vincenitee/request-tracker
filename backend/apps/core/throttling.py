"""Rate limits whose rates come from settings at request time (so they are configurable and testable)."""

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class ApiUserRateThrottle(UserRateThrottle):
    """General limit for the whole API: per user, or per IP for anonymous calls."""

    scope = "user"

    def get_rate(self):
        return settings.API_USER_THROTTLE_RATE


class LoginRateThrottle(AnonRateThrottle):
    """Brute-force guard for POST /auth/token/: per client IP, counts every attempt."""

    scope = "login"

    def get_rate(self):
        return settings.LOGIN_THROTTLE_RATE

    def get_cache_key(self, request, view):
        # AnonRateThrottle skips authenticated requests; the login endpoint is always keyed by IP.
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
