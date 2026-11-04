"""
Carrito de compras guardado en la sesión (django.contrib.sessions).

En la sesión solo se guarda {id_producto: cantidad}. Precio, nombre y stock se leen
siempre de la base, así un cambio de precio o un producto desactivado se refleja
enseguida y nadie puede "fijar" un precio manipulando la sesión.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from catalogo.models import Producto


class StockInsuficiente(Exception):
    def __init__(self, producto, disponible):
        self.producto = producto
        self.disponible = disponible
        if disponible <= 0:
            mensaje = f'"{producto.nombre}" está agotado.'
        else:
            mensaje = f'Solo hay {disponible} unidad{"es" if disponible != 1 else ""} de "{producto.nombre}".'
        super().__init__(mensaje)


@dataclass
class ItemCarrito:
    producto: Producto
    cantidad: int

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad

    @property
    def supera_stock(self):
        return self.cantidad > self.producto.stock


class Carrito:
    def __init__(self, request):
        self.session = request.session
        datos = self.session.get(settings.CARRITO_SESSION_ID)
        if not isinstance(datos, dict):
            datos = {}
        self._datos = datos
        self._items = None  # cache de items() dentro del mismo request

    # ----- Escritura -----

    def agregar(self, producto, cantidad=1, reemplazar=False):
        """Suma `cantidad` (o la reemplaza) validando que el total no supere el stock."""
        if cantidad < 1:
            raise ValueError('La cantidad debe ser al menos 1.')
        if not producto.activo:
            raise StockInsuficiente(producto, 0)
        clave = str(producto.pk)
        nueva = cantidad if reemplazar else self._datos.get(clave, 0) + cantidad
        if nueva > producto.stock:
            raise StockInsuficiente(producto, producto.stock)
        self._datos[clave] = nueva
        self._guardar()

    def quitar(self, producto_id):
        if self._datos.pop(str(producto_id), None) is not None:
            self._guardar()

    def vaciar(self):
        self._datos = {}
        self._guardar()

    def _guardar(self):
        self.session[settings.CARRITO_SESSION_ID] = self._datos
        self.session.modified = True
        self._items = None

    # ----- Lectura -----

    def items(self):
        """Items con su producto (una sola consulta). Descarta productos borrados o inactivos."""
        if self._items is None:
            ids = [int(clave) for clave in self._datos if clave.isdigit()]
            productos = Producto.objects.activos().con_categoria().in_bulk(ids)
            self._items = [
                ItemCarrito(productos[int(clave)], int(cantidad))
                for clave, cantidad in self._datos.items()
                if clave.isdigit() and int(clave) in productos and int(cantidad) > 0
            ]
            if len(self._items) != len(self._datos):
                # Se limpia lo que ya no se puede comprar
                self._datos = {str(item.producto.pk): item.cantidad for item in self._items}
                self.session[settings.CARRITO_SESSION_ID] = self._datos
                self.session.modified = True
        return self._items

    def __iter__(self):
        return iter(self.items())

    def __len__(self):
        """Cantidad total de unidades (para el contador del navbar)."""
        return sum(int(cantidad) for cantidad in self._datos.values())

    def cantidad_de(self, producto_id):
        return int(self._datos.get(str(producto_id), 0))

    @property
    def total(self):
        return sum((item.subtotal for item in self.items()), Decimal('0.00'))

    @property
    def esta_vacio(self):
        return not self.items()

    def problemas_de_stock(self):
        """Items cuyo stock bajó por debajo de lo que está en el carrito."""
        return [item for item in self.items() if item.supera_stock]
