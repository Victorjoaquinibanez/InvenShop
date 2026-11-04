from django.apps import AppConfig


class CarritoConfig(AppConfig):
    """El carrito no tiene modelos: vive en la sesión hasta que se confirma el pedido."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'carrito'
    verbose_name = 'Carrito'
