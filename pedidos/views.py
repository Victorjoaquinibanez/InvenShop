from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from carrito.carrito import Carrito, StockInsuficiente

from .forms import CambiarEstadoForm, DatosEnvioForm, FiltroPedidosForm
from .models import DetallePedido, Pedido, TransicionInvalida
from .servicios import CarritoVacio, crear_pedido_desde_carrito

SESION_ENVIO = 'checkout_envio'


def pedidos_con_detalles():
    """Pedido + usuario + detalles con su producto: 3 consultas sin importar cuántos productos haya."""
    return Pedido.objects.select_related('usuario').prefetch_related(
        Prefetch('detalles', queryset=DetallePedido.objects.select_related('producto', 'producto__categoria'))
    )


# ----- Checkout -----

class CheckoutMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Solo usuarios autenticados que pueden hacer pedidos, y con un carrito comprable."""

    permission_required = 'pedidos.add_pedido'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_permission():
            messages.warning(request, 'Tu cuenta es de personal: los pedidos los hacen los clientes.')
            return redirect('carrito:ver')
        self.carrito = Carrito(request)
        if self.carrito.esta_vacio:
            messages.info(request, 'Tu carrito está vacío.')
            return redirect('catalogo:lista')
        if self.carrito.problemas_de_stock():
            messages.warning(request, 'Algunos productos ya no tienen el stock que pediste. Revisá el carrito.')
            return redirect('carrito:ver')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['carrito'] = self.carrito
        return contexto


class CheckoutView(CheckoutMixin, FormView):
    """Paso 1: resumen del carrito y datos de envío."""

    form_class = DatosEnvioForm
    template_name = 'pedidos/checkout.html'

    def get_initial(self):
        guardados = self.request.session.get(SESION_ENVIO)
        if isinstance(guardados, dict):
            return guardados
        return {'telefono_contacto': self.request.user.telefono}

    def form_valid(self, form):
        self.request.session[SESION_ENVIO] = form.cleaned_data
        return redirect('pedidos:confirmar')


class ConfirmarPedidoView(CheckoutMixin, TemplateView):
    """Paso 2: confirmación final. Recién acá se registra el pedido y se descuenta el stock."""

    template_name = 'pedidos/confirmar.html'

    def datos_envio(self):
        datos = self.request.session.get(SESION_ENVIO)
        form = DatosEnvioForm(datos if isinstance(datos, dict) else None)
        return form.cleaned_data if form.is_valid() else None

    def get(self, request, *args, **kwargs):
        if self.datos_envio() is None:
            return redirect('pedidos:checkout')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['envio'] = self.datos_envio()
        return contexto

    def post(self, request, *args, **kwargs):
        datos = self.datos_envio()
        if datos is None:
            return redirect('pedidos:checkout')
        try:
            pedido = crear_pedido_desde_carrito(request.user, self.carrito, datos)
        except StockInsuficiente as error:
            messages.error(request, f'No se pudo registrar el pedido: {error} Ajustá el carrito y volvé a intentar.')
            return redirect('carrito:ver')
        except CarritoVacio:
            return redirect('catalogo:lista')
        request.session.pop(SESION_ENVIO, None)
        messages.success(request, f'¡Gracias! Registramos tu pedido #{pedido.numero}.')
        return redirect(pedido)


# ----- Historial y detalle -----

class MisPedidosView(LoginRequiredMixin, ListView):
    template_name = 'pedidos/mis_pedidos.html'
    context_object_name = 'pedidos'
    paginate_by = 10

    def get_queryset(self):
        # order_by explícito: con annotate (GROUP BY) Django no aplica el ordering del Meta
        return (Pedido.objects.filter(usuario=self.request.user)
                .annotate(cantidad_unidades=Sum('detalles__cantidad'))
                .order_by('-fecha_creacion', '-id'))


class PedidoDetailView(LoginRequiredMixin, DetailView):
    template_name = 'pedidos/detalle.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        consulta = pedidos_con_detalles()
        if self.request.user.has_perm('pedidos.ver_todos_los_pedidos'):
            return consulta
        # Un cliente solo ve los suyos: el de otro da 404 (no revela que existe)
        return consulta.filter(usuario=self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if self.request.user.has_perm('pedidos.cambiar_estado_pedido') and self.object.estados_siguientes():
            contexto['form_estado'] = CambiarEstadoForm(pedido=self.object)
        return contexto


# ----- Gestión (Empleado y Administrador) -----

class PedidoGestionListView(PermissionRequiredMixin, ListView):
    permission_required = 'pedidos.ver_todos_los_pedidos'
    template_name = 'pedidos/gestion_lista.html'
    context_object_name = 'pedidos'
    paginate_by = 20

    def get_queryset(self):
        consulta = (Pedido.objects.select_related('usuario')
                    .annotate(cantidad_unidades=Sum('detalles__cantidad'))
                    .order_by('-fecha_creacion', '-id'))
        self.filtro = FiltroPedidosForm(self.request.GET or None)
        if not self.filtro.is_valid():
            return consulta
        datos = self.filtro.cleaned_data
        texto = datos.get('q', '').strip().lstrip('#')
        if texto:
            condicion = (Q(usuario__email__icontains=texto) | Q(usuario__nombre__icontains=texto)
                         | Q(usuario__apellido__icontains=texto))
            if texto.isdigit():
                condicion |= Q(pk=int(texto))
            consulta = consulta.filter(condicion)
        if datos.get('estado'):
            consulta = consulta.filter(estado=datos['estado'])
        if datos.get('desde'):
            consulta = consulta.filter(fecha_creacion__date__gte=datos['desde'])
        if datos.get('hasta'):
            consulta = consulta.filter(fecha_creacion__date__lte=datos['hasta'])
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['filtro'] = self.filtro
        parametros = self.request.GET.copy()
        parametros.pop('page', None)
        contexto['querystring'] = parametros.urlencode()
        return contexto


class CambiarEstadoView(PermissionRequiredMixin, View):
    permission_required = 'pedidos.cambiar_estado_pedido'
    http_method_names = ['post']

    def post(self, request, pk):
        pedido = get_object_or_404(Pedido, pk=pk)
        form = CambiarEstadoForm(request.POST, pedido=pedido)
        if not form.is_valid():
            messages.error(request, 'Ese cambio de estado no está permitido.')
            return redirect(pedido)
        nuevo = form.cleaned_data['estado']
        try:
            pedido.cambiar_estado(nuevo)
        except TransicionInvalida as error:
            messages.error(request, str(error))
        else:
            extra = ' Se repuso el stock de sus productos.' if nuevo == Pedido.Estado.CANCELADO else ''
            messages.success(request, f'El pedido #{pedido.numero} pasó a {pedido.get_estado_display()}.{extra}')
        return redirect(pedido)
