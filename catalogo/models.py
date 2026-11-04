from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def slug_unico(instancia, texto, campo='slug'):
    """Slug a partir de `texto`, con -2, -3... si ya existe otro registro con el mismo."""
    base = slugify(texto)[:45] or 'item'
    slug, numero = base, 2
    modelo = type(instancia)
    while modelo.objects.filter(**{campo: slug}).exclude(pk=instancia.pk).exists():
        slug = f'{base}-{numero}'
        numero += 1
    return slug


class Categoria(models.Model):
    nombre = models.CharField('nombre', max_length=80, unique=True)
    descripcion = models.TextField('descripción', blank=True)
    slug = models.SlugField('slug', max_length=50, unique=True, blank=True,
                            help_text='Se genera solo a partir del nombre si se deja vacío.')

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unico(self, self.nombre)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('catalogo:lista')}?categoria={self.slug}"


class ProductoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)

    def con_categoria(self):
        # Evita una consulta por producto al mostrar la categoría (N+1)
        return self.select_related('categoria')


class Producto(models.Model):
    nombre = models.CharField('nombre', max_length=150)
    slug = models.SlugField('slug', max_length=60, unique=True, blank=True)
    descripcion = models.TextField('descripción', blank=True)
    precio = models.DecimalField('precio', max_digits=10, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.PositiveIntegerField('stock', default=0)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos',
                                  verbose_name='categoría')
    imagen = models.ImageField('imagen', upload_to='productos/', blank=True)
    activo = models.BooleanField('activo', default=True,
                                 help_text='Los productos inactivos no aparecen en el catálogo.')
    creado = models.DateTimeField('creado', auto_now_add=True)
    actualizado = models.DateTimeField('actualizado', auto_now=True)

    objects = ProductoQuerySet.as_manager()

    class Meta:
        verbose_name = 'producto'
        verbose_name_plural = 'productos'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activo', 'nombre']),
            models.Index(fields=['activo', 'precio']),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gt=0), name='producto_precio_positivo'),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unico(self, self.nombre)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('catalogo:detalle', kwargs={'slug': self.slug})

    @property
    def agotado(self):
        return self.stock <= 0
