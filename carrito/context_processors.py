from django.conf import settings


def carrito(request):
    """Cantidad de unidades en el carrito para el contador del navbar (sin consultar la base)."""
    datos = request.session.get(settings.CARRITO_SESSION_ID) if hasattr(request, 'session') else None
    if not isinstance(datos, dict):
        return {'carrito_cantidad': 0}
    return {'carrito_cantidad': sum(int(c) for c in datos.values() if str(c).isdigit())}
