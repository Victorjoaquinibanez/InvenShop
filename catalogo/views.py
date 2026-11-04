from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from carrito.forms import AgregarAlCarritoForm

from .forms import AjusteStockForm, CategoriaForm, FiltroCatalogoForm, ProductoForm
from .models import Categoria, Producto


def filtrar_productos(consulta, form):
    """Búsqueda + categoría + orden (combinables). `form` ya validado."""
    datos = form.cleaned_data if form.is_valid() else {}
    texto = (datos.get('q') or '').strip()
    if texto:
        consulta = consulta.filter(Q(nombre__icontains=texto) | Q(descripcion__icontains=texto))
    if datos.get('categoria'):
        consulta = consulta.filter(categoria=datos['categoria'])
    orden = datos.get('orden') or 'nombre'
    return consulta.order_by(orden, 'pk')


def querystring_sin_pagina(request):
    """Los filtros actuales, para que la paginación no los pierda."""
    parametros = request.GET.copy()
    parametros.pop('page', None)
    return parametros.urlencode()


# ----- Catálogo público -----

class ProductoListView(ListView):
    template_name = 'catalogo/lista.html'
    context_object_name = 'productos'
    paginate_by = 12

    def get_queryset(self):
        self.filtro = FiltroCatalogoForm(self.request.GET or None)
        return filtrar_productos(Producto.objects.activos().con_categoria(), self.filtro)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['filtro'] = self.filtro
        contexto['categorias'] = Categoria.objects.annotate(
            cantidad=Count('productos', filter=Q(productos__activo=True))
        ).filter(cantidad__gt=0)
        contexto['querystring'] = querystring_sin_pagina(self.request)
        return contexto


class ProductoDetailView(DetailView):
    template_name = 'catalogo/detalle.html'
    context_object_name = 'producto'

    def get_queryset(self):
        return Producto.objects.activos().con_categoria()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['form_carrito'] = AgregarAlCarritoForm(producto=self.object)
        contexto['relacionados'] = (
            Producto.objects.activos().filter(categoria=self.object.categoria, stock__gt=0)
            .exclude(pk=self.object.pk).con_categoria()[:4]
        )
        return contexto


# ----- Gestión de productos (Empleado y Administrador) -----

class ProductoGestionListView(PermissionRequiredMixin, ListView):
    permission_required = 'catalogo.view_producto'
    template_name = 'catalogo/gestion/productos_lista.html'
    context_object_name = 'productos'
    paginate_by = 20

    def get_queryset(self):
        self.filtro = FiltroCatalogoForm(self.request.GET or None)
        consulta = filtrar_productos(Producto.objects.con_categoria(), self.filtro)
        estado = self.request.GET.get('estado')
        if estado == 'activos':
            consulta = consulta.filter(activo=True)
        elif estado == 'inactivos':
            consulta = consulta.filter(activo=False)
        elif estado == 'sin_stock':
            consulta = consulta.filter(stock=0)
        elif estado == 'stock_bajo':
            consulta = consulta.filter(stock__gt=0, stock__lte=5)
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['filtro'] = self.filtro
        contexto['estado_actual'] = self.request.GET.get('estado', '')
        contexto['querystring'] = querystring_sin_pagina(self.request)
        return contexto


class ProductoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'catalogo.add_producto'
    model = Producto
    form_class = ProductoForm
    template_name = 'catalogo/gestion/producto_form.html'
    success_url = reverse_lazy('catalogo:gestion_productos')
    success_message = 'Se creó el producto "%(nombre)s".'


class ProductoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'catalogo.change_producto'
    model = Producto
    form_class = ProductoForm
    template_name = 'catalogo/gestion/producto_form.html'
    success_url = reverse_lazy('catalogo:gestion_productos')
    success_message = 'Se guardaron los cambios de "%(nombre)s".'


class ProductoDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'catalogo.delete_producto'
    model = Producto
    template_name = 'catalogo/gestion/confirmar_borrado.html'
    success_url = reverse_lazy('catalogo:gestion_productos')
    extra_context = {
        'volver_url': success_url,
        'aviso': 'Si el producto ya figura en pedidos no se podrá eliminar (se conserva para el historial); '
                 'en ese caso conviene desactivarlo.',
    }

    def form_valid(self, form):
        nombre = self.object.nombre
        try:
            self.object.delete()
        except ProtectedError:
            # Tiene pedidos: se conserva para el historial
            messages.error(self.request, f'"{nombre}" tiene pedidos registrados y no se puede eliminar. '
                                         'Podés desactivarlo para que no aparezca en el catálogo.')
            return redirect('catalogo:gestion_productos')
        messages.success(self.request, f'Se eliminó el producto "{nombre}".')
        return redirect(self.success_url)


@login_required
@permission_required('catalogo.change_producto', raise_exception=True)
@require_POST
def ajustar_stock(request, pk):
    """Edición rápida del stock desde el listado del panel."""
    producto = get_object_or_404(Producto, pk=pk)
    form = AjusteStockForm(request.POST)
    if form.is_valid():
        producto.stock = form.cleaned_data['stock']
        producto.save(update_fields=['stock', 'actualizado'])
        messages.success(request, f'Stock de "{producto.nombre}": {producto.stock}.')
    else:
        messages.error(request, 'El stock debe ser un número entero mayor o igual a 0.')
    siguiente = request.POST.get('siguiente', '')
    if siguiente.startswith('/') and not siguiente.startswith('//'):
        return redirect(siguiente)
    return redirect('catalogo:gestion_productos')


@login_required
@permission_required('catalogo.change_producto', raise_exception=True)
@require_POST
def alternar_activo(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    producto.activo = not producto.activo
    producto.save(update_fields=['activo', 'actualizado'])
    estado = 'visible en el catálogo' if producto.activo else 'oculto del catálogo'
    messages.success(request, f'"{producto.nombre}" quedó {estado}.')
    siguiente = request.POST.get('siguiente', '')
    if siguiente.startswith('/') and not siguiente.startswith('//'):
        return redirect(siguiente)
    return redirect('catalogo:gestion_productos')


# ----- Gestión de categorías -----

class CategoriaListView(PermissionRequiredMixin, ListView):
    permission_required = 'catalogo.view_categoria'
    template_name = 'catalogo/gestion/categorias_lista.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        return Categoria.objects.annotate(
            cantidad_productos=Count('productos'),
            cantidad_activos=Count('productos', filter=Q(productos__activo=True)),
        )


class CategoriaCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'catalogo.add_categoria'
    model = Categoria
    form_class = CategoriaForm
    template_name = 'catalogo/gestion/categoria_form.html'
    success_url = reverse_lazy('catalogo:gestion_categorias')
    success_message = 'Se creó la categoría "%(nombre)s".'


class CategoriaUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'catalogo.change_categoria'
    model = Categoria
    form_class = CategoriaForm
    template_name = 'catalogo/gestion/categoria_form.html'
    success_url = reverse_lazy('catalogo:gestion_categorias')
    success_message = 'Se guardaron los cambios de "%(nombre)s".'


class CategoriaDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'catalogo.delete_categoria'
    model = Categoria
    template_name = 'catalogo/gestion/confirmar_borrado.html'
    success_url = reverse_lazy('catalogo:gestion_categorias')
    extra_context = {
        'volver_url': success_url,
        'aviso': 'Si la categoría tiene productos no se podrá eliminar: primero hay que moverlos a otra.',
    }

    def form_valid(self, form):
        nombre = self.object.nombre
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(self.request, f'La categoría "{nombre}" tiene productos y no se puede eliminar.')
            return redirect('catalogo:gestion_categorias')
        messages.success(self.request, f'Se eliminó la categoría "{nombre}".')
        return redirect(self.success_url)
