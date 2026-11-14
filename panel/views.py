from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django.views.generic import TemplateView

from catalogo.models import Producto
from pedidos.models import DetallePedido, Pedido

STOCK_BAJO = 5
CERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))

# Ventas que cuentan como concretadas (lo pendiente puede no pagarse y lo cancelado no suma)
ESTADOS_VENDIDOS = [Pedido.Estado.PAGADO, Pedido.Estado.ENVIADO]


class InicioPanelView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Inicio del panel: lo que el personal tiene que atender hoy."""

    permission_required = 'catalogo.view_producto'  # Empleado y Administrador
    template_name = 'panel/inicio.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        por_estado = dict(Pedido.objects.values_list('estado').annotate(cantidad=Count('id')))
        contexto['pedidos_por_estado'] = [
            (estado, por_estado.get(estado.value, 0)) for estado in Pedido.Estado
        ]
        contexto['productos_activos'] = Producto.objects.filter(activo=True).count()
        contexto['productos_agotados'] = Producto.objects.filter(activo=True, stock=0).count()
        contexto['stock_bajo'] = (Producto.objects.filter(activo=True, stock__gt=0, stock__lte=STOCK_BAJO)
                                  .con_categoria().order_by('stock', 'nombre')[:8])
        contexto['ultimos_pendientes'] = (Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE)
                                          .select_related('usuario')[:6])
        contexto['umbral_stock'] = STOCK_BAJO
        return contexto


class ReportesView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Reportes de ventas (solo Administrador)."""

    permission_required = 'pedidos.ver_reportes'
    template_name = 'panel/reportes.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        vendidos = Pedido.objects.filter(estado__in=ESTADOS_VENDIDOS)

        resumen = vendidos.aggregate(facturado=Coalesce(Sum('total'), CERO), cantidad=Count('id'))
        resumen['ticket_promedio'] = resumen['facturado'] / resumen['cantidad'] if resumen['cantidad'] else 0
        contexto['resumen'] = resumen

        hace_un_anio = timezone.now() - timedelta(days=365)
        contexto['ventas_por_mes'] = list(
            vendidos.filter(fecha_creacion__gte=hace_un_anio)
            .annotate(mes=TruncMonth('fecha_creacion')).values('mes')
            .annotate(facturado=Sum('total'), cantidad=Count('id')).order_by('mes')
        )

        detalles_vendidos = DetallePedido.objects.filter(pedido__estado__in=ESTADOS_VENDIDOS)
        contexto['mas_vendidos'] = (
            detalles_vendidos.values('producto__nombre', 'producto__categoria__nombre')
            .annotate(unidades=Sum('cantidad'), facturado=Sum(F('cantidad') * F('precio_unitario')))
            .order_by('-unidades', 'producto__nombre')[:10]
        )
        contexto['por_categoria'] = (
            detalles_vendidos.values('producto__categoria__nombre')
            .annotate(unidades=Sum('cantidad'), facturado=Sum(F('cantidad') * F('precio_unitario')))
            .order_by('-facturado')
        )
        contexto['mejores_clientes'] = (
            vendidos.values('usuario__nombre', 'usuario__apellido', 'usuario__email')
            .annotate(pedidos=Count('id'), facturado=Sum('total')).order_by('-facturado')[:5]
        )
        contexto['cancelados'] = Pedido.objects.filter(estado=Pedido.Estado.CANCELADO).count()
        return contexto
