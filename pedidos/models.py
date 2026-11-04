from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse

from catalogo.models import Producto


class TransicionInvalida(Exception):
    """Se intentó pasar un pedido a un estado que no corresponde."""


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'Pendiente', 'Pendiente'
        PAGADO = 'Pagado', 'Pagado'
        ENVIADO = 'Enviado', 'Enviado'
        CANCELADO = 'Cancelado', 'Cancelado'

    # Pendiente → Pagado → Enviado; Cancelado desde Pendiente o Pagado (lo enviado ya no se cancela)
    TRANSICIONES = {
        Estado.PENDIENTE: [Estado.PAGADO, Estado.CANCELADO],
        Estado.PAGADO: [Estado.ENVIADO, Estado.CANCELADO],
        Estado.ENVIADO: [],
        Estado.CANCELADO: [],
    }

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pedidos',
                                verbose_name='usuario')
    fecha_creacion = models.DateTimeField('fecha de creación', auto_now_add=True)
    estado = models.CharField('estado', max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.DecimalField('total', max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Datos de envío
    direccion = models.CharField('dirección', max_length=200)
    ciudad = models.CharField('ciudad', max_length=100)
    codigo_postal = models.CharField('código postal', max_length=10)
    telefono_contacto = models.CharField('teléfono de contacto', max_length=20)

    class Meta:
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'
        ordering = ['-fecha_creacion', '-id']
        indexes = [models.Index(fields=['estado', 'fecha_creacion'])]
        permissions = [
            ('cambiar_estado_pedido', 'Puede cambiar el estado de los pedidos'),
            ('ver_todos_los_pedidos', 'Puede ver los pedidos de todos los clientes'),
            ('ver_reportes', 'Puede ver los reportes de ventas'),
        ]

    def __str__(self):
        return f'Pedido #{self.numero}'

    def get_absolute_url(self):
        return reverse('pedidos:detalle', kwargs={'pk': self.pk})

    @property
    def numero(self):
        return f'{self.pk:06d}' if self.pk else '—'

    def estados_siguientes(self):
        return self.TRANSICIONES[self.Estado(self.estado)]

    def puede_pasar_a(self, nuevo_estado):
        return nuevo_estado in self.estados_siguientes()

    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado validando la transición. Al cancelar, devuelve el stock de cada producto."""
        with transaction.atomic():
            # Se relee bloqueado para que dos empleados no cancelen el mismo pedido a la vez
            pedido = Pedido.objects.select_for_update().get(pk=self.pk)
            if not pedido.puede_pasar_a(nuevo_estado):
                raise TransicionInvalida(
                    f'Un pedido {pedido.get_estado_display().lower()} no puede pasar a {Pedido.Estado(nuevo_estado).label.lower()}.'
                )
            if nuevo_estado == self.Estado.CANCELADO:
                for producto_id, cantidad in pedido.detalles.values_list('producto_id', 'cantidad'):
                    Producto.objects.filter(pk=producto_id).update(stock=F('stock') + cantidad)
            pedido.estado = nuevo_estado
            pedido.save(update_fields=['estado'])
        self.estado = nuevo_estado


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles', verbose_name='pedido')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_pedido',
                                 verbose_name='producto')
    cantidad = models.PositiveIntegerField('cantidad', validators=[MinValueValidator(1)])
    # Precio al momento de la compra: si después cambia el precio del producto, el pedido no se altera
    precio_unitario = models.DecimalField('precio unitario', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'detalle del pedido'
        verbose_name_plural = 'detalles del pedido'
        constraints = [
            models.UniqueConstraint(fields=['pedido', 'producto'], name='detalle_producto_unico_por_pedido'),
            models.CheckConstraint(condition=models.Q(cantidad__gte=1), name='detalle_cantidad_positiva'),
        ]

    def __str__(self):
        return f'{self.cantidad} × {self.producto}'

    @property
    def subtotal(self):
        if self.cantidad is None or self.precio_unitario is None:
            return Decimal('0.00')
        return self.cantidad * self.precio_unitario
