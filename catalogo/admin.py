from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'cantidad_productos']
    search_fields = ['nombre', 'descripcion']
    prepopulated_fields = {'slug': ['nombre']}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_cantidad=Count('productos'))

    @admin.display(description='productos', ordering='_cantidad')
    def cantidad_productos(self, obj):
        return obj._cantidad


class StockFilter(admin.SimpleListFilter):
    title = 'stock'
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        return [('agotado', 'Agotado'), ('bajo', 'Bajo (1 a 5)'), ('disponible', 'Más de 5')]

    def queryset(self, request, queryset):
        if self.value() == 'agotado':
            return queryset.filter(stock=0)
        if self.value() == 'bajo':
            return queryset.filter(stock__gte=1, stock__lte=5)
        if self.value() == 'disponible':
            return queryset.filter(stock__gt=5)
        return queryset


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['miniatura', 'nombre', 'categoria', 'precio', 'stock', 'activo', 'actualizado']
    list_display_links = ['miniatura', 'nombre']
    list_editable = ['stock', 'activo']  # edición rápida desde el listado
    list_filter = ['categoria', 'activo', StockFilter, ('creado', admin.DateFieldListFilter)]
    search_fields = ['nombre', 'descripcion', 'categoria__nombre']
    list_select_related = ['categoria']  # evita N+1 al mostrar la categoría
    list_per_page = 25
    prepopulated_fields = {'slug': ['nombre']}
    readonly_fields = ['creado', 'actualizado', 'vista_imagen']
    fieldsets = [
        (None, {'fields': ['nombre', 'slug', 'categoria', 'descripcion']}),
        ('Precio y stock', {'fields': ['precio', 'stock', 'activo']}),
        ('Imagen', {'fields': ['imagen', 'vista_imagen']}),
        ('Fechas', {'fields': ['creado', 'actualizado'], 'classes': ['collapse']}),
    ]
    actions = ['activar', 'desactivar']

    @admin.display(description='')
    def miniatura(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:4px">',
                               obj.imagen.url)
        return '—'

    @admin.display(description='vista previa')
    def vista_imagen(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-height:200px;border-radius:6px">', obj.imagen.url)
        return 'Sin imagen'

    @admin.action(description='Activar los productos seleccionados')
    def activar(self, request, queryset):
        cantidad = queryset.update(activo=True)
        self.message_user(request, f'{cantidad} producto(s) activado(s).')

    @admin.action(description='Desactivar los productos seleccionados')
    def desactivar(self, request, queryset):
        cantidad = queryset.update(activo=False)
        self.message_user(request, f'{cantidad} producto(s) desactivado(s).')
