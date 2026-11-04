from django import forms

from usuarios.forms import BootstrapMixin

from .models import Categoria, Producto


class FiltroCatalogoForm(BootstrapMixin, forms.Form):
    ORDENES = [
        ('nombre', 'Nombre (A-Z)'),
        ('-nombre', 'Nombre (Z-A)'),
        ('precio', 'Menor precio'),
        ('-precio', 'Mayor precio'),
    ]

    q = forms.CharField(label='Buscar', required=False, max_length=100,
                        widget=forms.TextInput(attrs={'placeholder': 'Buscar por nombre o descripción', 'type': 'search'}))
    categoria = forms.ModelChoiceField(label='Categoría', queryset=Categoria.objects.all(), required=False,
                                       to_field_name='slug', empty_label='Todas las categorías')
    orden = forms.ChoiceField(label='Ordenar por', choices=ORDENES, required=False)


class ProductoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'descripcion', 'precio', 'stock', 'imagen', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'precio': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
        }

    def clean_nombre(self):
        return ' '.join(self.cleaned_data['nombre'].split())

    def clean(self):
        datos = super().clean()
        nombre, categoria = datos.get('nombre'), datos.get('categoria')
        if nombre and categoria:
            repetido = Producto.objects.filter(nombre__iexact=nombre, categoria=categoria).exclude(pk=self.instance.pk)
            if repetido.exists():
                self.add_error('nombre', 'Ya hay un producto con ese nombre en la categoría elegida.')
        return datos

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and hasattr(imagen, 'size') and imagen.size > 2 * 1024 * 1024:
            raise forms.ValidationError('La imagen no puede pesar más de 2 MB.')
        return imagen


class CategoriaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'slug']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}

    def clean_nombre(self):
        nombre = ' '.join(self.cleaned_data['nombre'].split())
        repetida = Categoria.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError('Ya existe una categoría con ese nombre.')
        return nombre


class AjusteStockForm(BootstrapMixin, forms.Form):
    """Ajuste rápido de stock desde el listado del panel."""

    stock = forms.IntegerField(label='Stock', min_value=0, max_value=1_000_000)
