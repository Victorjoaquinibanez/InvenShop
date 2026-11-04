from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Producto
from usuarios.models import Usuario

from .models import Pedido

ENVIO = {'direccion': 'Belgrano 123', 'ciudad': 'santiago del estero',
         'codigo_postal': 'g4200abc', 'telefono_contacto': '385 400-1234'}


class FlujoDeCompraTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre='Almacén')
        self.yerba = Producto.objects.create(nombre='Yerba', precio=Decimal('1000.00'), stock=5, categoria=categoria)
        self.arroz = Producto.objects.create(nombre='Arroz', precio=Decimal('500.00'), stock=2, categoria=categoria)
        self.cliente = Usuario.objects.create_user('cli@mail.com', 'x', nombre='Cli', apellido='Ente')
        self.otro = Usuario.objects.create_user('otro@mail.com', 'x', nombre='Otro', apellido='Cliente')
        self.empleado = Usuario.objects.create_user('emp@mail.com', 'x', nombre='Em', apellido='P',
                                                    rol=Usuario.Rol.EMPLEADO)

    def agregar(self, producto, cantidad):
        return self.client.post(reverse('carrito:agregar', args=[producto.pk]), {'cantidad': cantidad})

    def comprar(self):
        self.client.post(reverse('pedidos:checkout'), ENVIO)
        return self.client.post(reverse('pedidos:confirmar'))

    # ----- Carrito -----

    def test_carrito_no_supera_el_stock(self):
        self.agregar(self.arroz, 2)
        respuesta = self.agregar(self.arroz, 1)
        self.assertEqual(self.client.session['carrito'], {str(self.arroz.pk): 2})
        mensajes = [str(m) for m in get_messages(respuesta.wsgi_request)]
        self.assertIn('Solo hay 2 unidades de "Arroz".', mensajes)

    def test_carrito_calcula_total_y_se_puede_modificar(self):
        self.agregar(self.yerba, 2)
        self.agregar(self.arroz, 1)
        self.client.post(reverse('carrito:actualizar', args=[self.yerba.pk]), {'cantidad': 3})
        respuesta = self.client.get(reverse('carrito:ver'))
        self.assertEqual(respuesta.context['carrito'].total, Decimal('3500.00'))
        self.client.post(reverse('carrito:quitar', args=[self.arroz.pk]))
        self.assertEqual(self.client.session['carrito'], {str(self.yerba.pk): 3})
        self.client.post(reverse('carrito:vaciar'))
        self.assertEqual(self.client.session['carrito'], {})

    def test_carrito_se_conserva_al_iniciar_sesion(self):
        self.agregar(self.yerba, 1)
        self.client.post(reverse('usuarios:login'), {'username': 'cli@mail.com', 'password': 'x'})
        self.assertEqual(self.client.session['carrito'], {str(self.yerba.pk): 1})

    # ----- Checkout -----

    def test_checkout_requiere_login(self):
        self.agregar(self.yerba, 1)
        respuesta = self.client.get(reverse('pedidos:checkout'))
        self.assertRedirects(respuesta, f"{reverse('usuarios:login')}?next={reverse('pedidos:checkout')}")

    def test_compra_completa_descuenta_stock_y_vacia_carrito(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 2)
        self.agregar(self.arroz, 2)

        respuesta = self.client.post(reverse('pedidos:checkout'), ENVIO)
        self.assertRedirects(respuesta, reverse('pedidos:confirmar'))
        self.assertFalse(Pedido.objects.exists())  # todavía falta la confirmación final

        respuesta = self.client.post(reverse('pedidos:confirmar'))
        pedido = Pedido.objects.get()
        self.assertRedirects(respuesta, pedido.get_absolute_url())
        self.assertEqual(pedido.total, Decimal('3000.00'))
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertEqual(pedido.codigo_postal, 'G4200ABC')
        self.assertEqual(pedido.ciudad, 'Santiago Del Estero')
        self.assertEqual(pedido.detalles.count(), 2)
        self.yerba.refresh_from_db()
        self.arroz.refresh_from_db()
        self.assertEqual((self.yerba.stock, self.arroz.stock), (3, 0))
        self.assertEqual(self.client.session['carrito'], {})

    def test_si_el_stock_cambio_no_se_registra_nada(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 2)
        self.agregar(self.arroz, 2)
        self.client.post(reverse('pedidos:checkout'), ENVIO)
        Producto.objects.filter(pk=self.arroz.pk).update(stock=1)  # otro cliente compró mientras tanto

        self.client.post(reverse('pedidos:confirmar'))
        self.assertFalse(Pedido.objects.exists())
        self.yerba.refresh_from_db()
        self.assertEqual(self.yerba.stock, 5)  # tampoco quedó descontado lo que sí alcanzaba

    def test_validaciones_de_envio(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 1)
        respuesta = self.client.post(reverse('pedidos:checkout'), {
            'direccion': 'Sin número', 'ciudad': 'C1ud4d', 'codigo_postal': '12', 'telefono_contacto': 'abc',
        })
        errores = respuesta.context['form'].errors
        self.assertEqual(set(errores), {'direccion', 'ciudad', 'codigo_postal', 'telefono_contacto'})

    def test_personal_no_hace_pedidos(self):
        self.client.force_login(self.empleado)
        self.agregar(self.yerba, 1)
        respuesta = self.client.get(reverse('pedidos:checkout'))
        self.assertRedirects(respuesta, reverse('carrito:ver'))

    # ----- Historial y estados -----

    def test_cliente_solo_ve_sus_pedidos(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 1)
        self.comprar()
        pedido = Pedido.objects.get()

        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(pedido.get_absolute_url()).status_code, 404)
        self.assertEqual(len(self.client.get(reverse('pedidos:mis_pedidos')).context['pedidos']), 0)

        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(pedido.get_absolute_url()).status_code, 200)

    def test_cliente_no_cambia_estados(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 1)
        self.comprar()
        pedido = Pedido.objects.get()
        respuesta = self.client.post(reverse('pedidos:cambiar_estado', args=[pedido.pk]), {'estado': 'Pagado'})
        self.assertEqual(respuesta.status_code, 403)

    def test_cancelar_repone_stock_y_respeta_transiciones(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 3)
        self.comprar()
        pedido = Pedido.objects.get()

        self.client.force_login(self.empleado)
        url = reverse('pedidos:cambiar_estado', args=[pedido.pk])
        self.client.post(url, {'estado': 'Enviado'})  # Pendiente → Enviado no está permitido
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)

        self.client.post(url, {'estado': 'Cancelado'})
        pedido.refresh_from_db()
        self.yerba.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.CANCELADO)
        self.assertEqual(self.yerba.stock, 5)

        self.client.post(url, {'estado': 'Cancelado'})  # cancelar dos veces no repone dos veces
        self.yerba.refresh_from_db()
        self.assertEqual(self.yerba.stock, 5)

    def test_detalle_del_pedido_sin_n_mas_1(self):
        self.client.force_login(self.cliente)
        self.agregar(self.yerba, 1)
        self.agregar(self.arroz, 1)
        self.comprar()
        pedido = Pedido.objects.get()
        self.client.force_login(self.empleado)
        # sesión, usuario, permisos (2), pedido+cliente, detalles+productos+categoría
        with self.assertNumQueries(6):
            self.client.get(pedido.get_absolute_url())
