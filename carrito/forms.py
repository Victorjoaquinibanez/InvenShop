from django import forms


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(label='Cantidad', min_value=1, initial=1,
                                  widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto is not None:
            self.fields['cantidad'].max_value = max(producto.stock, 1)
            self.fields['cantidad'].widget.attrs['max'] = max(producto.stock, 1)


class ActualizarCantidadForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1, max_value=10_000)
