from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import CambiarPasswordForm, LoginForm, PerfilForm, RegistroForm, UsuarioRolForm
from .models import Usuario


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = 'usuarios/registro.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('usuarios:inicio_segun_rol')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        usuario = form.save()
        login(self.request, usuario)
        messages.success(self.request, f'¡Bienvenido/a, {usuario.nombre}! Tu cuenta quedó creada.')
        return redirect('catalogo:lista')


class IniciarSesionView(LoginView):
    form_class = LoginForm
    template_name = 'usuarios/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f'Hola, {self.request.user.nombre}.')
        return respuesta


class CerrarSesionView(LogoutView):
    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        messages.info(request, 'Cerraste la sesión.')
        return respuesta


@login_required
def inicio_segun_rol(request):
    """Destino después del login (si no vino ?next=): personal al panel, clientes al catálogo."""
    if request.user.es_personal:
        return redirect('panel:inicio')
    return redirect('catalogo:lista')


class PerfilView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = PerfilForm
    template_name = 'usuarios/perfil.html'
    success_url = reverse_lazy('usuarios:perfil')
    success_message = 'Tus datos se actualizaron.'

    def get_object(self, queryset=None):
        # Cada usuario solo ve y edita su propio perfil: no hay id en la URL.
        # Copia aparte de request.user para que un formulario con errores no cambie el nombre del navbar.
        return Usuario.objects.get(pk=self.request.user.pk)


class CambiarPasswordView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    form_class = CambiarPasswordForm
    template_name = 'usuarios/cambiar_password.html'
    success_url = reverse_lazy('usuarios:perfil')
    success_message = 'Tu contraseña se cambió correctamente.'


# ----- Gestión de usuarios (solo Administrador) -----

class UsuarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'usuarios.view_usuario'
    template_name = 'usuarios/gestion_lista.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        consulta = Usuario.objects.annotate(cantidad_pedidos=Count('pedidos')).order_by('apellido', 'nombre')
        texto = self.request.GET.get('q', '').strip()
        if texto:
            consulta = consulta.filter(
                Q(email__icontains=texto) | Q(nombre__icontains=texto) | Q(apellido__icontains=texto)
            )
        rol = self.request.GET.get('rol')
        if rol in Usuario.Rol.values:
            consulta = consulta.filter(rol=rol)
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['roles'] = Usuario.Rol.choices
        contexto['q'] = self.request.GET.get('q', '')
        contexto['rol_actual'] = self.request.GET.get('rol', '')
        return contexto


class UsuarioRolUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'usuarios.change_usuario'
    model = Usuario
    form_class = UsuarioRolForm
    template_name = 'usuarios/gestion_editar.html'
    context_object_name = 'usuario_editado'
    success_url = reverse_lazy('usuarios:gestion_lista')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['editor'] = self.request.user
        return kwargs

    def get_success_message(self, cleaned_data):
        return f'Se actualizó la cuenta de {self.object.nombre_completo}.'
