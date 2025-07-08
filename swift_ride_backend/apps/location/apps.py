from django.apps import AppConfig


class LocationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.location'
    verbose_name = 'Location Services'

    def ready(self):
        import apps.location.signals
