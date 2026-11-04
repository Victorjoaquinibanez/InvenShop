"""Creación de pedidos a partir del carrito, dentro de una transacción."""

from django.db import transaction
from django.db.models import F

from carrito.carrito import StockInsuficiente
from catalogo.models import Producto

from .models import DetallePedido, Pedido


class CarritoVacio(Exception):
    pass


def crear_pedido_desde_carrito(usuario, carrito, datos_envio):
    """
    Registra el pedido y descuenta el stock. Todo o nada: si un producto no alcanza,
    se revierte y no queda ni el pedido ni ningún descuento a medias.

    El descuento es un UPDATE condicional (stock >= cantidad): si dos clientes compran
    la última unidad al mismo tiempo, solo uno de los dos UPDATE afecta la fila.
    """
    items = carrito.items()
    if not items:
        raise CarritoVacio('El carrito está vacío.')

    with transaction.atomic():
        pedido = Pedido.objects.create(usuario=usuario, **datos_envio)
        detalles = []
        total = 0
        for item in items:
            actualizadas = Producto.objects.filter(
                pk=item.producto.pk, activo=True, stock__gte=item.cantidad
            ).update(stock=F('stock') - item.cantidad)
            if not actualizadas:
                item.producto.refresh_from_db(fields=['stock', 'activo'])
                raise StockInsuficiente(item.producto, item.producto.stock if item.producto.activo else 0)

            detalles.append(DetallePedido(
                pedido=pedido, producto=item.producto,
                cantidad=item.cantidad, precio_unitario=item.producto.precio,
            ))
            total += item.subtotal

        DetallePedido.objects.bulk_create(detalles)
        pedido.total = total
        pedido.save(update_fields=['total'])

    carrito.vaciar()
    return pedido
