from django.apps import AppConfig


class ServiceRequestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.service_requests'

    def ready(self):
        from . import signals  # noqa: F401  (connects the receivers)
