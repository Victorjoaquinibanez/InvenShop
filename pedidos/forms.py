import re

from django import forms

from usuarios.forms import BootstrapMixin, validar_telefono

from .models import Pedido

# Código postal argentino: 4 dígitos (4200) o CPA (G4200ABC)
CODIGO_POSTAL_RE = re.compile(r'^(\d{4}|[A-Z]\d{4}[A-Z]{3})$')
CIUDAD_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'\-]{2,100}$")


class DatosEnvioForm(BootstrapMixin, forms.Form):
    direccion = forms.CharField(label='Dirección', max_length=200,
                                widget=forms.TextInput(attrs={'placeholder': 'Calle, número, piso/depto.',
                                                              'autocomplete': 'street-address'}))
    ciudad = forms.CharField(label='Ciudad', max_length=100,
                             widget=forms.TextInput(attrs={'autocomplete': 'address-level2'}))
    codigo_postal = forms.CharField(label='Código postal', max_length=10,
                                    widget=forms.TextInput(attrs={'placeholder': '4200 o G4200ABC',
                                                                  'autocomplete': 'postal-code'}))
    telefono_contacto = forms.CharField(label='Teléfono de contacto', max_length=20,
                                        widget=forms.TextInput(attrs={'autocomplete': 'tel'}))

    def clean_direccion(self):
        direccion = ' '.join(self.cleaned_data['direccion'].split())
        if len(direccion) < 5:
            raise forms.ValidationError('La dirección es demasiado corta.')
        if not re.search(r'\d', direccion):
            raise forms.ValidationError('Incluí la altura (número) de la calle.')
        return direccion

    def clean_ciudad(self):
        ciudad = ' '.join(self.cleaned_data['ciudad'].split())
        if not CIUDAD_RE.match(ciudad):
            raise forms.ValidationError('La ciudad solo puede tener letras, espacios, puntos y guiones.')
        return ciudad.title()

    def clean_codigo_postal(self):
        codigo = self.cleaned_data['codigo_postal'].replace(' ', '').upper()
        if not CODIGO_POSTAL_RE.match(codigo):
            raise forms.ValidationError('Ingresá un código postal válido: 4 dígitos (4200) o CPA (G4200ABC).')
        return codigo

    def clean_telefono_contacto(self):
        telefono = validar_telefono(self.cleaned_data.get('telefono_contacto'))
        if not telefono:
            raise forms.ValidationError('El teléfono de contacto es obligatorio.')
        return telefono


class CambiarEstadoForm(BootstrapMixin, forms.Form):
    estado = forms.ChoiceField(label='Nuevo estado', choices=Pedido.Estado.choices)

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido
        if pedido is not None:
            # Solo se ofrecen los estados a los que puede pasar
            self.fields['estado'].choices = [(e.value, e.label) for e in pedido.estados_siguientes()]

    def clean_estado(self):
        estado = self.cleaned_data['estado']
        if self.pedido is not None and not self.pedido.puede_pasar_a(estado):
            raise forms.ValidationError('Ese cambio de estado no está permitido.')
        return estado


class FiltroPedidosForm(BootstrapMixin, forms.Form):
    q = forms.CharField(label='Buscar', required=False, max_length=100,
                        widget=forms.TextInput(attrs={'placeholder': 'N° de pedido, email o nombre', 'type': 'search'}))
    estado = forms.ChoiceField(label='Estado', required=False,
                               choices=[('', 'Todos los estados')] + list(Pedido.Estado.choices))
    desde = forms.DateField(label='Desde', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(label='Hasta', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        datos = super().clean()
        if datos.get('desde') and datos.get('hasta') and datos['desde'] > datos['hasta']:
            raise forms.ValidationError('La fecha "desde" no puede ser posterior a "hasta".')
        return datos
