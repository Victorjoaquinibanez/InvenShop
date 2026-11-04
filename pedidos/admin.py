from django.contrib import admin, messages
from django.db.models import Sum

from .models import DetallePedido, Pedido, TransicionInvalida


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']
    # Datos históricos de la compra: no se modifican después de confirmado el pedido
    readonly_fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('producto')

    @admin.display(description='subtotal')
    def subtotal(self, obj):
        return f'$ {obj.subtotal:,.2f}'


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero_pedido', 'usuario', 'fecha_creacion', 'estado', 'unidades', 'total']
    list_filter = ['estado', ('fecha_creacion', admin.DateFieldListFilter)]
    search_fields = ['=id', 'usuario__email', 'usuario__nombre', 'usuario__apellido']
    search_help_text = 'Buscar por número de pedido (exacto) o por email / nombre del cliente.'
    list_select_related = ['usuario']
    date_hierarchy = 'fecha_creacion'
    inlines = [DetallePedidoInline]
    readonly_fields = ['usuario', 'fecha_creacion', 'estado', 'total',
                       'direccion', 'ciudad', 'codigo_postal', 'telefono_contacto']
    fieldsets = [
        (None, {'fields': ['usuario', 'fecha_creacion', 'estado', 'total']}),
        ('Envío', {'fields': ['direccion', 'ciudad', 'codigo_postal', 'telefono_contacto']}),
    ]
    actions = ['marcar_pagado', 'marcar_enviado', 'marcar_cancelado']

    def has_add_permission(self, request):
        # Los pedidos se crean desde el checkout (descuenta stock en una transacción)
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_unidades=Sum('detalles__cantidad'))

    @admin.display(description='N°', ordering='id')
    def numero_pedido(self, obj):
        return f'#{obj.numero}'

    @admin.display(description='unidades', ordering='_unidades')
    def unidades(self, obj):
        return obj._unidades or 0

    def _cambiar_estado(self, request, queryset, estado):
        if not request.user.has_perm('pedidos.cambiar_estado_pedido'):
            self.message_user(request, 'No tenés permiso para cambiar estados.', messages.ERROR)
            return
        cambiados, rechazados = 0, []
        for pedido in queryset:
            try:
                pedido.cambiar_estado(estado)
                cambiados += 1
            except TransicionInvalida:
                rechazados.append(f'#{pedido.numero}')
        if cambiados:
            self.message_user(request, f'{cambiados} pedido(s) pasaron a {estado}.', messages.SUCCESS)
        if rechazados:
            self.message_user(request, f'No se pudieron pasar a {estado}: {", ".join(rechazados)}.', messages.WARNING)

    @admin.action(description='Marcar como Pagado', permissions=['change'])
    def marcar_pagado(self, request, queryset):
        self._cambiar_estado(request, queryset, Pedido.Estado.PAGADO)

    @admin.action(description='Marcar como Enviado', permissions=['change'])
    def marcar_enviado(self, request, queryset):
        self._cambiar_estado(request, queryset, Pedido.Estado.ENVIADO)

    @admin.action(description='Cancelar (repone el stock)', permissions=['change'])
    def marcar_cancelado(self, request, queryset):
        self._cambiar_estado(request, queryset, Pedido.Estado.CANCELADO)
