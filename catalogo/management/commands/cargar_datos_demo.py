"""
Carga datos de prueba: categorías, productos, un usuario por rol y algunos pedidos.

    python manage.py cargar_datos_demo

Se puede correr varias veces: no duplica lo que ya existe.
"""

from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.models import Categoria, Producto
from pedidos.models import Pedido
from pedidos.servicios import crear_pedido_desde_carrito
from usuarios.models import Usuario

PASSWORD_DEMO = 'InvenShop2026!'

CATALOGO = {
    'Almacén': ('Alimentos secos y envasados.', [
        ('Yerba mate 1 kg', 'Yerba mate con palo, molienda tradicional.', '4850.00', 40),
        ('Arroz largo fino 1 kg', 'Arroz tipo 00000, ideal para guarniciones.', '1650.00', 60),
        ('Fideos tirabuzón 500 g', 'Pasta seca de sémola de trigo candeal.', '980.00', 75),
        ('Aceite de girasol 1,5 L', 'Aceite refinado de girasol.', '3200.00', 4),
        ('Azúcar 1 kg', 'Azúcar blanca refinada.', '1350.00', 0),
    ]),
    'Bebidas': ('Gaseosas, aguas y jugos.', [
        ('Agua mineral 2 L', 'Agua mineral sin gas.', '890.00', 120),
        ('Gaseosa cola 2,25 L', 'Bebida gaseosa sabor cola.', '2450.00', 50),
        ('Jugo de naranja 1 L', 'Jugo exprimido, sin azúcar agregada.', '2100.00', 3),
    ]),
    'Limpieza': ('Artículos de limpieza para el hogar.', [
        ('Detergente 750 ml', 'Detergente concentrado aroma limón.', '1890.00', 35),
        ('Lavandina 2 L', 'Lavandina concentrada.', '1250.00', 45),
        ('Esponja doble faz x3', 'Pack de tres esponjas.', '990.00', 2),
    ]),
    'Librería': ('Útiles escolares y de oficina.', [
        ('Cuaderno universitario 84 h', 'Rayado, tapa dura.', '3400.00', 25),
        ('Birome azul x10', 'Caja de diez biromes trazo medio.', '2900.00', 30),
        ('Resma A4 500 hojas', 'Papel de 75 g/m².', '7800.00', 12),
    ]),
    'Electrónica': ('Accesorios y pequeños electrónicos.', [
        ('Auriculares in-ear', 'Auriculares con micrófono, conector 3,5 mm.', '8900.00', 15),
        ('Cargador USB-C 20 W', 'Carga rápida, compatible con la mayoría de los celulares.', '12500.00', 8),
        ('Mouse inalámbrico', 'Mouse óptico 1600 dpi con receptor USB.', '9700.00', 0),
    ]),
}

# Fotos de los productos de prueba (están en el repositorio; media/ no se sube a git)
CARPETA_IMAGENES = Path(__file__).resolve().parents[2] / 'datos_demo' / 'imagenes'
IMAGENES = {
    'Aceite de girasol 1,5 L': 'aceite-girasol.webp',
    'Agua mineral 2 L': 'agua-mineral.webp',
    'Arroz largo fino 1 kg': 'arroz-largo-fino.jpg',
    'Auriculares in-ear': 'auriculares-in-ear.jpg',
    'Azúcar 1 kg': 'azucar-1kg.jpg',
    'Birome azul x10': 'birome-azul-x10.jpg',
    'Cargador USB-C 20 W': 'cargador-usb-c-20w.jpg',
    'Cuaderno universitario 84 h': 'cuaderno-universitario-84h.jpg',
    'Detergente 750 ml': 'detergente-750ml.jpg',
    'Esponja doble faz x3': 'esponja-doble-faz-x3.jpg',
    'Fideos tirabuzón 500 g': 'fideos-tirabuzon-500g.jpg',
    'Gaseosa cola 2,25 L': 'gaseosa-cola-2-25l.jpg',
    'Jugo de naranja 1 L': 'jugo-naranja-1l.jpg',
    'Lavandina 2 L': 'lavandina-2l.jpg',
    'Mouse inalámbrico': 'mouse-inalambrico.jpg',
    'Resma A4 500 hojas': 'resma-a4-500-hojas.jpg',
    'Yerba mate 1 kg': 'yerba-mate-1kg.jpg',
}

USUARIOS = [
    ('admin@invenshop.com', 'Ana', 'Administradora', Usuario.Rol.ADMIN),
    ('empleado@invenshop.com', 'Esteban', 'Empleado', Usuario.Rol.EMPLEADO),
    ('cliente@invenshop.com', 'Carla', 'Cliente', Usuario.Rol.CLIENTE),
]


class SesionFalsa(dict):
    """Para reutilizar el Carrito (que vive en la sesión) desde un comando."""

    modified = False


class PedidoFalso:
    def __init__(self):
        self.session = SesionFalsa()


class Command(BaseCommand):
    help = 'Carga categorías, productos, usuarios de prueba (uno por rol) y algunos pedidos.'

    @transaction.atomic
    def handle(self, *args, **options):
        productos_nuevos = 0
        for nombre_categoria, (descripcion, productos) in CATALOGO.items():
            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria,
                                                           defaults={'descripcion': descripcion})
            for nombre, desc, precio, stock in productos:
                _, creado = Producto.objects.get_or_create(
                    nombre=nombre, categoria=categoria,
                    defaults={'descripcion': desc, 'precio': Decimal(precio), 'stock': stock},
                )
                productos_nuevos += creado

        imagenes_cargadas = self._cargar_imagenes()

        usuarios = {}
        for email, nombre, apellido, rol in USUARIOS:
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                crear = Usuario.objects.create_superuser if rol == Usuario.Rol.ADMIN else Usuario.objects.create_user
                usuario = crear(email, PASSWORD_DEMO, nombre=nombre, apellido=apellido, rol=rol, telefono='385 400-0000')
            usuarios[rol] = usuario

        cliente = usuarios[Usuario.Rol.CLIENTE]
        if not cliente.pedidos.exists():
            self._pedidos_de_ejemplo(cliente)

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {Categoria.objects.count()} categorías, {Producto.objects.count()} productos '
            f'({productos_nuevos} nuevos, {imagenes_cargadas} imágenes cargadas), {Pedido.objects.count()} pedidos.'
        ))
        self.stdout.write('Usuarios de prueba (contraseña: %s):' % PASSWORD_DEMO)
        for email, _, _, rol in USUARIOS:
            self.stdout.write(f'  {Usuario.Rol(rol).label:<14} {email}')

    def _cargar_imagenes(self):
        """Asigna la foto a los productos que todavía no tienen (no pisa una imagen ya cargada)."""
        cargadas = 0
        for nombre, archivo in IMAGENES.items():
            producto = Producto.objects.filter(nombre=nombre).first()
            ruta = CARPETA_IMAGENES / archivo
            if producto is None or producto.imagen or not ruta.exists():
                continue
            with ruta.open('rb') as imagen:
                producto.imagen.save(archivo, File(imagen), save=True)
            cargadas += 1
        return cargadas

    def _pedidos_de_ejemplo(self, cliente):
        from carrito.carrito import Carrito

        envio = {'direccion': 'Av. Belgrano Sur 1234', 'ciudad': 'Santiago Del Estero',
                 'codigo_postal': '4200', 'telefono_contacto': '385 400-0000'}
        compras = [
            ([('Yerba mate 1 kg', 2), ('Agua mineral 2 L', 6)], Pedido.Estado.ENVIADO),
            ([('Cuaderno universitario 84 h', 3), ('Birome azul x10', 1)], Pedido.Estado.PAGADO),
            ([('Detergente 750 ml', 2), ('Auriculares in-ear', 1)], Pedido.Estado.PENDIENTE),
        ]
        for items, estado_final in compras:
            carrito = Carrito(PedidoFalso())
            for nombre, cantidad in items:
                carrito.agregar(Producto.objects.get(nombre=nombre), cantidad)
            pedido = crear_pedido_desde_carrito(cliente, carrito, envio)
            if estado_final in (Pedido.Estado.PAGADO, Pedido.Estado.ENVIADO):
                pedido.cambiar_estado(Pedido.Estado.PAGADO)
            if estado_final == Pedido.Estado.ENVIADO:
                pedido.cambiar_estado(Pedido.Estado.ENVIADO)
