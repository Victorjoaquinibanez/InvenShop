from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from catalogo.models import Producto

from .carrito import Carrito, StockInsuficiente
from .forms import ActualizarCantidadForm, AgregarAlCarritoForm


def volver(request, por_defecto='carrito:ver'):
    """Redirige a ?siguiente= si es una ruta interna (evita redirecciones a otros sitios)."""
    siguiente = request.POST.get('siguiente', '')
    if url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(siguiente)
    return redirect(por_defecto)


class CarritoView(TemplateView):
    template_name = 'carrito/ver.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        carrito = Carrito(self.request)
        contexto['carrito'] = carrito
        contexto['problemas_stock'] = carrito.problemas_de_stock()
        return contexto


class AgregarView(View):
    http_method_names = ['post']

    def post(self, request, producto_id):
        producto = get_object_or_404(Producto.objects.activos(), pk=producto_id)
        form = AgregarAlCarritoForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Indicá una cantidad válida.')
            return volver(request, producto.get_absolute_url())
        try:
            Carrito(request).agregar(producto, form.cleaned_data['cantidad'])
        except StockInsuficiente as error:
            messages.warning(request, str(error))
            return volver(request, producto.get_absolute_url())
        messages.success(request, f'Agregaste "{producto.nombre}" al carrito.')
        return volver(request)


class ActualizarView(View):
    http_method_names = ['post']

    def post(self, request, producto_id):
        producto = get_object_or_404(Producto.objects.activos(), pk=producto_id)
        form = ActualizarCantidadForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'La cantidad debe ser un número mayor a 0.')
            return redirect('carrito:ver')
        try:
            Carrito(request).agregar(producto, form.cleaned_data['cantidad'], reemplazar=True)
        except StockInsuficiente as error:
            messages.warning(request, str(error))
        else:
            messages.success(request, f'Cantidad de "{producto.nombre}" actualizada.')
        return redirect('carrito:ver')


class QuitarView(View):
    http_method_names = ['post']

    def post(self, request, producto_id):
        Carrito(request).quitar(producto_id)
        messages.info(request, 'Se quitó el producto del carrito.')
        return redirect('carrito:ver')


class VaciarView(View):
    http_method_names = ['post']

    def post(self, request):
        Carrito(request).vaciar()
        messages.info(request, 'Vaciaste el carrito.')
        return redirect('carrito:ver')
