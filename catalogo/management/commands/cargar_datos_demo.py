"""
Carga datos de prueba: categorías, productos, usuarios de cada rol y pedidos de los últimos meses.

    python manage.py cargar_datos_demo

Se puede correr varias veces: no duplica lo que ya existe.
"""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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

# (email, nombre, apellido, rol, teléfono, dirección, ciudad, código postal)
# El personal usa el dominio del comercio; los clientes, example.com (dominio reservado para ejemplos)
USUARIOS = [
    ('ana.gomez@invenshop.com', 'Ana', 'Gómez', Usuario.Rol.ADMIN,
     '385 421-3390', 'Av. Belgrano Sur 1450', 'Santiago Del Estero', '4200'),
    ('esteban.ruiz@invenshop.com', 'Esteban', 'Ruiz', Usuario.Rol.EMPLEADO,
     '385 433-1187', 'Pellegrini 655', 'Santiago Del Estero', '4200'),
    ('carla.medina@example.com', 'Carla', 'Medina', Usuario.Rol.CLIENTE,
     '385 512-4471', 'Av. Libertad 1234', 'Santiago Del Estero', '4200'),
    ('martin.herrera@example.com', 'Martín', 'Herrera', Usuario.Rol.CLIENTE,
     '385 598-2260', 'Independencia 873', 'Santiago Del Estero', '4200'),
    ('sofia.ledesma@example.com', 'Sofía', 'Ledesma', Usuario.Rol.CLIENTE,
     '385 467-9015', 'Besares 412', 'La Banda', '4300'),
    ('julian.paz@example.com', 'Julián', 'Paz', Usuario.Rol.CLIENTE,
     '385 530-7748', 'Av. Roca 2210', 'Santiago Del Estero', 'G4200ABC'),
    ('valentina.rios@example.com', 'Valentina', 'Ríos', Usuario.Rol.CLIENTE,
     '385 482-3356', 'Mitre 1580', 'La Banda', '4300'),
]

# Pedidos de ejemplo: (hace cuántos días, email del cliente, productos, estado final).
# Repartidos en seis meses para que los reportes por mes tengan datos.
PEDIDOS = [
    (170, 'carla.medina@example.com', [('Yerba mate 1 kg', 2), ('Agua mineral 2 L', 6)], 'Enviado'),
    (160, 'martin.herrera@example.com', [('Resma A4 500 hojas', 1), ('Birome azul x10', 1)], 'Enviado'),
    (140, 'sofia.ledesma@example.com', [('Detergente 750 ml', 2), ('Lavandina 2 L', 2)], 'Enviado'),
    (120, 'julian.paz@example.com', [('Auriculares in-ear', 1)], 'Enviado'),
    (110, 'carla.medina@example.com', [('Fideos tirabuzón 500 g', 4), ('Arroz largo fino 1 kg', 2),
                                       ('Gaseosa cola 2,25 L', 2)], 'Enviado'),
    (95, 'valentina.rios@example.com', [('Cuaderno universitario 84 h', 3), ('Birome azul x10', 1)], 'Enviado'),
    (80, 'martin.herrera@example.com', [('Cargador USB-C 20 W', 1)], 'Cancelado'),
    (70, 'sofia.ledesma@example.com', [('Yerba mate 1 kg', 1), ('Gaseosa cola 2,25 L', 2)], 'Enviado'),
    (55, 'julian.paz@example.com', [('Resma A4 500 hojas', 2)], 'Enviado'),
    (40, 'carla.medina@example.com', [('Detergente 750 ml', 1), ('Lavandina 2 L', 1),
                                      ('Agua mineral 2 L', 4)], 'Enviado'),
    (25, 'valentina.rios@example.com', [('Auriculares in-ear', 1), ('Cargador USB-C 20 W', 1)], 'Enviado'),
    (12, 'martin.herrera@example.com', [('Fideos tirabuzón 500 g', 3), ('Arroz largo fino 1 kg', 2)], 'Pagado'),
    (6, 'sofia.ledesma@example.com', [('Cuaderno universitario 84 h', 2)], 'Pagado'),
    (3, 'julian.paz@example.com', [('Gaseosa cola 2,25 L', 1), ('Agua mineral 2 L', 2)], 'Cancelado'),
    (1, 'carla.medina@example.com', [('Detergente 750 ml', 2), ('Auriculares in-ear', 1)], 'Pendiente'),
    (0, 'valentina.rios@example.com', [('Yerba mate 1 kg', 2), ('Birome azul x10', 1)], 'Pendiente'),
]

# Estados por los que pasa cada pedido hasta su estado final (respetando las transiciones del modelo)
CAMINO = {
    'Pendiente': [],
    'Pagado': ['Pagado'],
    'Enviado': ['Pagado', 'Enviado'],
    'Cancelado': ['Cancelado'],
}


class SesionFalsa(dict):
    """Para reutilizar el Carrito (que vive en la sesión) desde un comando."""

    modified = False


class PedidoFalso:
    def __init__(self):
        self.session = SesionFalsa()


class Command(BaseCommand):
    help = 'Carga categorías, productos, usuarios de prueba de cada rol y pedidos de los últimos meses.'

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
        for email, nombre, apellido, rol, telefono, *_ in USUARIOS:
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                crear = Usuario.objects.create_superuser if rol == Usuario.Rol.ADMIN else Usuario.objects.create_user
                usuario = crear(email, PASSWORD_DEMO, nombre=nombre, apellido=apellido, rol=rol, telefono=telefono)
            usuarios[email] = usuario

        # Solo en una base sin pedidos, para no mezclarlos con pedidos reales
        if not Pedido.objects.exists():
            self._pedidos_de_ejemplo(usuarios)

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {Categoria.objects.count()} categorías, {Producto.objects.count()} productos '
            f'({productos_nuevos} nuevos, {imagenes_cargadas} imágenes cargadas), {Pedido.objects.count()} pedidos.'
        ))
        self.stdout.write('Usuarios de prueba (contraseña: %s):' % PASSWORD_DEMO)
        for email, nombre, apellido, rol, *_ in USUARIOS:
            self.stdout.write(f'  {Usuario.Rol(rol).label:<14} {email:<30} {nombre} {apellido}')

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

    def _pedidos_de_ejemplo(self, usuarios):
        """Crea los pedidos con el mismo servicio que usa la tienda, así el stock queda coherente."""
        from carrito.carrito import Carrito

        datos = {email: (telefono, direccion, ciudad, cp) for email, *_, telefono, direccion, ciudad, cp in USUARIOS}
        ahora = timezone.now()
        for dias, email, items, estado_final in PEDIDOS:
            telefono, direccion, ciudad, codigo_postal = datos[email]
            envio = {'direccion': direccion, 'ciudad': ciudad,
                     'codigo_postal': codigo_postal, 'telefono_contacto': telefono}
            carrito = Carrito(PedidoFalso())
            for nombre, cantidad in items:
                carrito.agregar(Producto.objects.get(nombre=nombre), cantidad)
            pedido = crear_pedido_desde_carrito(usuarios[email], carrito, envio)
            for estado in CAMINO[estado_final]:
                pedido.cambiar_estado(estado)
            # La fecha se pone en el pasado (auto_now_add no deja elegirla al crear)
            fecha = ahora - timedelta(days=dias, hours=dias % 9, minutes=(dias * 7) % 60)
            Pedido.objects.filter(pk=pedido.pk).update(fecha_creacion=fecha)
