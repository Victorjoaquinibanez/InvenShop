from django.test import TestCase
from django.urls import reverse

from .models import Usuario

PASSWORD = 'ClaveSegura2026!'


class RegistroYLoginTests(TestCase):
    def test_registro_crea_cliente_y_lo_deja_logueado(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'email': 'Nuevo@Mail.com', 'nombre': 'Nora', 'apellido': 'Nueva', 'telefono': '385 411-2233',
            'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertRedirects(respuesta, reverse('catalogo:lista'))
        usuario = Usuario.objects.get(email='nuevo@mail.com')
        self.assertEqual(usuario.rol, Usuario.Rol.CLIENTE)
        self.assertTrue(usuario.groups.filter(name='Cliente').exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

    def test_registro_rechaza_email_repetido_sin_importar_mayusculas(self):
        Usuario.objects.create_user('ya@existe.com', PASSWORD, nombre='Ya', apellido='Existe')
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'email': 'YA@existe.com', 'nombre': 'Otro', 'apellido': 'Más',
            'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertContains(respuesta, 'Ya existe una cuenta con ese email.')

    def test_registro_aplica_validadores_de_password(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'email': 'debil@mail.com', 'nombre': 'Deb', 'apellido': 'Il',
            'password1': '12345678', 'password2': '12345678',
        })
        self.assertFalse(Usuario.objects.filter(email='debil@mail.com').exists())
        self.assertTrue(respuesta.context['form'].errors['password1'])

    def test_registro_no_permite_elegir_rol(self):
        self.client.post(reverse('usuarios:registro'), {
            'email': 'pillo@mail.com', 'nombre': 'Pi', 'apellido': 'Llo', 'rol': 'Admin',
            'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(Usuario.objects.get(email='pillo@mail.com').rol, Usuario.Rol.CLIENTE)

    def test_login_redirige_segun_rol(self):
        Usuario.objects.create_user('c@mail.com', PASSWORD, nombre='C', apellido='C')
        Usuario.objects.create_user('e@mail.com', PASSWORD, nombre='E', apellido='E', rol=Usuario.Rol.EMPLEADO)

        respuesta = self.client.post(reverse('usuarios:login'), {'username': 'c@mail.com', 'password': PASSWORD}, follow=True)
        self.assertEqual(respuesta.redirect_chain[-1][0], reverse('catalogo:lista'))

        self.client.post(reverse('usuarios:logout'))
        respuesta = self.client.post(reverse('usuarios:login'), {'username': 'E@mail.com', 'password': PASSWORD}, follow=True)
        self.assertEqual(respuesta.redirect_chain[-1][0], reverse('panel:inicio'))

    def test_login_con_credenciales_invalidas_muestra_mensaje(self):
        respuesta = self.client.post(reverse('usuarios:login'), {'username': 'nadie@mail.com', 'password': 'x'})
        self.assertContains(respuesta, 'Email o contraseña incorrectos.')


class RolesYPermisosTests(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user('cli@mail.com', PASSWORD, nombre='Cli', apellido='Ente')
        self.empleado = Usuario.objects.create_user('emp@mail.com', PASSWORD, nombre='Em', apellido='Pleado',
                                                    rol=Usuario.Rol.EMPLEADO)
        self.admin = Usuario.objects.create_superuser('adm@mail.com', PASSWORD, nombre='Ad', apellido='Min')

    def test_el_rol_define_grupo_y_acceso_al_admin(self):
        self.assertFalse(self.cliente.is_staff)
        self.assertTrue(self.empleado.is_staff)
        self.assertTrue(self.empleado.has_perm('catalogo.change_producto'))
        self.assertFalse(self.empleado.has_perm('usuarios.change_usuario'))
        self.assertFalse(self.cliente.has_perm('catalogo.change_producto'))

    def test_cambiar_rol_cambia_el_grupo(self):
        self.cliente.rol = Usuario.Rol.EMPLEADO
        self.cliente.save()
        self.assertEqual(list(self.cliente.groups.values_list('name', flat=True)), ['Empleado'])

    def test_empleado_no_accede_a_gestion_de_usuarios(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('usuarios:gestion_lista')).status_code, 403)
        self.assertEqual(self.client.get(reverse('panel:reportes')).status_code, 403)

    def test_cliente_no_accede_al_panel(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse('panel:inicio')).status_code, 403)
        self.assertEqual(self.client.get(reverse('catalogo:gestion_productos')).status_code, 403)

    def test_anonimo_es_enviado_al_login(self):
        respuesta = self.client.get(reverse('panel:inicio'))
        self.assertRedirects(respuesta, f"{reverse('usuarios:login')}?next={reverse('panel:inicio')}")

    def test_admin_cambia_rol_pero_no_el_suyo(self):
        self.client.force_login(self.admin)
        url = reverse('usuarios:gestion_editar', args=[self.cliente.pk])
        self.client.post(url, {'rol': Usuario.Rol.EMPLEADO, 'is_active': 'on'})
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.rol, Usuario.Rol.EMPLEADO)

        respuesta = self.client.post(reverse('usuarios:gestion_editar', args=[self.admin.pk]),
                                     {'rol': Usuario.Rol.CLIENTE, 'is_active': 'on'})
        self.assertContains(respuesta, 'No podés quitarte el rol de Administrador')

    def test_perfil_solo_edita_al_usuario_logueado(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('usuarios:perfil'), {'nombre': 'Nuevo', 'apellido': 'Apellido', 'telefono': '385 400-1111'})
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, 'Nuevo')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nombre, 'Ad')
