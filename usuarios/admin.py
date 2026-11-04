from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count

from .forms import AdminUsuarioChangeForm, AdminUsuarioCreationForm
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = AdminUsuarioChangeForm
    add_form = AdminUsuarioCreationForm

    list_display = ['email', 'nombre', 'apellido', 'rol', 'telefono', 'is_active', 'cantidad_pedidos', 'date_joined']
    list_filter = ['rol', 'is_active', ('date_joined', admin.DateFieldListFilter)]
    search_fields = ['email', 'nombre', 'apellido', 'telefono']
    ordering = ['apellido', 'nombre']
    readonly_fields = ['is_staff', 'last_login', 'date_joined']

    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Datos personales', {'fields': ['nombre', 'apellido', 'telefono']}),
        ('Rol y acceso', {
            'fields': ['rol', 'is_active', 'is_staff', 'is_superuser'],
            'description': 'Los permisos los da el rol (grupo Administrador / Empleado / Cliente).',
        }),
        ('Fechas', {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {
            'classes': ['wide'],
            'fields': ['email', 'nombre', 'apellido', 'telefono', 'rol', 'password1', 'password2'],
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_cantidad_pedidos=Count('pedidos'))

    @admin.display(description='pedidos', ordering='_cantidad_pedidos')
    def cantidad_pedidos(self, obj):
        return obj._cantidad_pedidos
