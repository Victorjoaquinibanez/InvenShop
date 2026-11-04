from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    """Manager del usuario propio: se identifica por email, no por username."""

    use_in_migrations = True

    def _crear(self, email, password, **campos):
        if not email:
            raise ValueError('El email es obligatorio.')
        usuario = self.model(email=self.normalize_email(email).lower(), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **campos):
        campos.setdefault('rol', Usuario.Rol.CLIENTE)
        campos.setdefault('is_superuser', False)
        return self._crear(email, password, **campos)

    def create_superuser(self, email, password=None, **campos):
        campos['rol'] = Usuario.Rol.ADMIN
        campos['is_superuser'] = True
        return self._crear(email, password, **campos)

    def get_by_natural_key(self, email):
        # El login no distingue mayúsculas en el email
        return self.get(email__iexact=email)


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        ADMIN = 'Admin', 'Administrador'
        EMPLEADO = 'Empleado', 'Empleado'
        CLIENTE = 'Cliente', 'Cliente'

    email = models.EmailField('email', unique=True)
    nombre = models.CharField('nombre', max_length=80)
    apellido = models.CharField('apellido', max_length=80)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    rol = models.CharField('rol', max_length=10, choices=Rol.choices, default=Rol.CLIENTE)

    is_active = models.BooleanField('activo', default=True)
    is_staff = models.BooleanField(
        'acceso al admin', default=False, editable=False,
        help_text='Se calcula a partir del rol: Administrador y Empleado entran al admin de Django.',
    )
    date_joined = models.DateTimeField('fecha de alta', default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.nombre_completo} <{self.email}>'

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        # El personal (Admin y Empleado) entra al admin; los permisos concretos los da el grupo del rol
        self.is_staff = self.rol in (self.Rol.ADMIN, self.Rol.EMPLEADO)
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'.strip()

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN

    @property
    def es_personal(self):
        """Empleado o Administrador: los que usan el panel de gestión."""
        return self.rol in (self.Rol.ADMIN, self.Rol.EMPLEADO)
