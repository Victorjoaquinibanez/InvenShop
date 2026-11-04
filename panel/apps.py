from django.apps import AppConfig


class PanelConfig(AppConfig):
    """Panel de gestión para el personal (inicio con resumen y reportes). Sin modelos propios."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'panel'
    verbose_name = 'Panel de gestión'
