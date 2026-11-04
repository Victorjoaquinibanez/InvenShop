"""
Roles del sistema expresados como grupos de Django.

Cada rol es un Group con sus permisos; al guardar un usuario queda en el grupo de su rol
(ver signals.py). Así las vistas usan PermissionRequiredMixin / @permission_required
con los permisos estándar de Django, y el admin respeta los mismos permisos.
"""

from django.contrib.auth.models import Group, Permission

from .models import Usuario

# Permisos de cada rol como 'app_label.codename'. '__all__' = todos los permisos.
PERMISOS_POR_ROL = {
    Usuario.Rol.ADMIN: '__all__',
    Usuario.Rol.EMPLEADO: [
        # Productos, categorías y stock
        'catalogo.view_categoria', 'catalogo.add_categoria', 'catalogo.change_categoria', 'catalogo.delete_categoria',
        'catalogo.view_producto', 'catalogo.add_producto', 'catalogo.change_producto', 'catalogo.delete_producto',
        # Pedidos: ver todos y actualizar el estado (sin administrar usuarios)
        'pedidos.view_pedido', 'pedidos.change_pedido', 'pedidos.cambiar_estado_pedido', 'pedidos.ver_todos_los_pedidos',
        'pedidos.view_detallepedido',
    ],
    Usuario.Rol.CLIENTE: [
        # Realizar pedidos; su historial lo filtran las vistas por usuario
        'pedidos.add_pedido',
    ],
}


def nombre_grupo(rol):
    return Usuario.Rol(rol).label


def sincronizar_grupos():
    """Crea o actualiza los grupos de los roles con sus permisos. Es idempotente."""
    for rol, permisos in PERMISOS_POR_ROL.items():
        grupo, _ = Group.objects.get_or_create(name=nombre_grupo(rol))
        if permisos == '__all__':
            grupo.permissions.set(Permission.objects.all())
            continue
        objetos = []
        for permiso in permisos:
            app_label, codename = permiso.split('.')
            objetos.extend(Permission.objects.filter(content_type__app_label=app_label, codename=codename))
        grupo.permissions.set(objetos)


def asignar_grupo_del_rol(usuario):
    """Deja al usuario solo en el grupo de su rol (los grupos ajenos a los roles no se tocan)."""
    nombres_roles = [nombre_grupo(rol) for rol in Usuario.Rol.values]
    grupo, _ = Group.objects.get_or_create(name=nombre_grupo(usuario.rol))
    usuario.groups.remove(*usuario.groups.filter(name__in=nombres_roles).exclude(pk=grupo.pk))
    usuario.groups.add(grupo)
