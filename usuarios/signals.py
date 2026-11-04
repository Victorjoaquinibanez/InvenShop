from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Usuario
from .roles import asignar_grupo_del_rol, sincronizar_grupos


@receiver(post_save, sender=Usuario)
def grupo_segun_rol(sender, instance, raw=False, **kwargs):
    # raw = carga de fixtures (loaddata): ahí los grupos vienen en los datos
    if not raw:
        asignar_grupo_del_rol(instance)


def crear_grupos_de_roles(sender, **kwargs):
    # post_migrate llega una vez por app; los permisos de cada app recién existen cuando le toca,
    # así que se (re)arman los grupos cada vez (es idempotente y barato)
    sincronizar_grupos()


def conectar_post_migrate(app_config):
    post_migrate.connect(crear_grupos_de_roles, dispatch_uid='usuarios_grupos_roles')
