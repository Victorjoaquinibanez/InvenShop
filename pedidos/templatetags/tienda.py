from django import template
from django.utils.html import format_html

register = template.Library()

CLASES_ESTADO = {
    'Pendiente': ('text-bg-warning', 'bi-hourglass-split'),
    'Pagado': ('text-bg-info', 'bi-credit-card'),
    'Enviado': ('text-bg-success', 'bi-truck'),
    'Cancelado': ('text-bg-secondary', 'bi-x-circle'),
}


@register.simple_tag
def badge_estado(estado):
    """Etiqueta de color con ícono y texto (el estado no se comunica solo con el color)."""
    clase, icono = CLASES_ESTADO.get(estado, ('text-bg-light', 'bi-question-circle'))
    return format_html('<span class="badge {}"><i class="bi {}"></i> {}</span>', clase, icono, estado)


@register.filter
def pesos(valor):
    """$ 12.345,67 (formato argentino)."""
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return valor
    texto = f'{numero:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'$ {texto}'
