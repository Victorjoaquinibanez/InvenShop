from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

from .models import Categoria, Producto


class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bebidas = Categoria.objects.create(nombre='Bebidas')
        cls.almacen = Categoria.objects.create(nombre='Almacén')
        cls.agua = Producto.objects.create(nombre='Agua', descripcion='Sin gas', precio=Decimal('900'), stock=5,
                                           categoria=cls.bebidas)
        cls.jugo = Producto.objects.create(nombre='Jugo', descripcion='De naranja', precio=Decimal('2000'), stock=0,
                                           categoria=cls.bebidas)
        cls.arroz = Producto.objects.create(nombre='Arroz', descripcion='Largo fino', precio=Decimal('1500'), stock=9,
                                            categoria=cls.almacen)
        cls.oculto = Producto.objects.create(nombre='Oculto', precio=Decimal('100'), stock=9, categoria=cls.almacen,
                                             activo=False)

    def nombres(self, respuesta):
        return [p.nombre for p in respuesta.context['productos']]

    def test_solo_muestra_activos(self):
        respuesta = self.client.get(reverse('catalogo:lista'))
        self.assertNotIn('Oculto', self.nombres(respuesta))
        self.assertEqual(self.client.get(self.oculto.get_absolute_url()).status_code, 404)

    def test_filtro_por_categoria_y_busqueda_combinables(self):
        respuesta = self.client.get(reverse('catalogo:lista'), {'categoria': 'bebidas', 'q': 'naranja'})
        self.assertEqual(self.nombres(respuesta), ['Jugo'])

    def test_orden_por_precio(self):
        respuesta = self.client.get(reverse('catalogo:lista'), {'orden': '-precio'})
        self.assertEqual(self.nombres(respuesta), ['Jugo', 'Arroz', 'Agua'])

    def test_agotado_se_marca_y_no_tiene_boton_de_agregar(self):
        respuesta = self.client.get(self.jugo.get_absolute_url())
        self.assertContains(respuesta, 'Agotado')
        self.assertNotContains(respuesta, reverse('carrito:agregar', args=[self.jugo.pk]))

    def test_listado_sin_consultas_n_mas_1(self):
        for i in range(10):
            Producto.objects.create(nombre=f'Extra {i}', precio=Decimal('10'), stock=1, categoria=self.almacen)
        # conteo + categorías del <select> + categorías del costado + productos con su categoría:
        # siempre 4, sin importar cuántos productos haya
        with self.assertNumQueries(4):
            self.client.get(reverse('catalogo:lista'))

    def test_slug_unico(self):
        otro = Producto.objects.create(nombre='Agua', precio=Decimal('1'), stock=1, categoria=self.almacen)
        self.assertEqual(otro.slug, 'agua-2')


class GestionProductosTests(TestCase):
    def setUp(self):
        self.empleado = Usuario.objects.create_user('emp@mail.com', 'x', nombre='E', apellido='E',
                                                    rol=Usuario.Rol.EMPLEADO)
        self.categoria = Categoria.objects.create(nombre='Varios')
        self.client.force_login(self.empleado)

    def test_empleado_crea_producto(self):
        respuesta = self.client.post(reverse('catalogo:producto_crear'), {
            'nombre': '  Taza   cerámica ', 'categoria': self.categoria.pk, 'descripcion': '',
            'precio': '1500.50', 'stock': '7', 'activo': 'on',
        })
        self.assertRedirects(respuesta, reverse('catalogo:gestion_productos'))
        self.assertTrue(Producto.objects.filter(nombre='Taza cerámica', stock=7).exists())

    def test_precio_debe_ser_positivo(self):
        respuesta = self.client.post(reverse('catalogo:producto_crear'), {
            'nombre': 'Gratis', 'categoria': self.categoria.pk, 'precio': '0', 'stock': '1',
        })
        self.assertTrue(respuesta.context['form'].errors['precio'])

    def test_ajuste_rapido_de_stock(self):
        producto = Producto.objects.create(nombre='Vaso', precio=Decimal('10'), stock=1, categoria=self.categoria)
        self.client.post(reverse('catalogo:producto_stock', args=[producto.pk]), {'stock': '25'})
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 25)

    def test_ajuste_de_stock_solo_por_post(self):
        producto = Producto.objects.create(nombre='Plato', precio=Decimal('10'), stock=1, categoria=self.categoria)
        self.assertEqual(self.client.get(reverse('catalogo:producto_stock', args=[producto.pk])).status_code, 405)

    def test_no_se_borra_categoria_con_productos(self):
        Producto.objects.create(nombre='Vaso', precio=Decimal('10'), stock=1, categoria=self.categoria)
        self.client.post(reverse('catalogo:categoria_eliminar', args=[self.categoria.pk]))
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())

    def test_siguiente_solo_acepta_rutas_internas(self):
        producto = Producto.objects.create(nombre='Jarra', precio=Decimal('10'), stock=1, categoria=self.categoria)
        url = reverse('catalogo:producto_stock', args=[producto.pk])
        interna = reverse('catalogo:gestion_productos') + '?pagina=2'
        respuesta = self.client.post(url, {'stock': '3', 'siguiente': interna})
        self.assertRedirects(respuesta, interna, fetch_redirect_response=False)
        # Open redirect (Clase 7): otros sitios, incluido el truco '/\sitio', vuelven al listado
        for externa in ['https://evil.com/', '//evil.com/', r'/\evil.com']:
            respuesta = self.client.post(url, {'stock': '3', 'siguiente': externa})
            self.assertRedirects(respuesta, reverse('catalogo:gestion_productos'), fetch_redirect_response=False)

    def test_anonimo_va_al_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse('catalogo:gestion_productos'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta['Location'])
