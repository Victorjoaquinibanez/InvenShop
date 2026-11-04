from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.RegistroView.as_view(), name='registro'),
    path('ingresar/', views.IniciarSesionView.as_view(), name='login'),
    path('salir/', views.CerrarSesionView.as_view(), name='logout'),
    path('inicio/', views.inicio_segun_rol, name='inicio_segun_rol'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('perfil/contrasena/', views.CambiarPasswordView.as_view(), name='cambiar_password'),

    path('gestion/', views.UsuarioListView.as_view(), name='gestion_lista'),
    path('gestion/<int:pk>/', views.UsuarioRolUpdateView.as_view(), name='gestion_editar'),
]
