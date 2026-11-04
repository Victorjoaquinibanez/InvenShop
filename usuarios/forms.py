import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, ReadOnlyPasswordHashField

from .models import Usuario

TELEFONO_RE = re.compile(r'^\+?[\d\s\-()]{6,20}$')


def validar_telefono(valor):
    valor = (valor or '').strip()
    if valor and (not TELEFONO_RE.match(valor) or len(re.sub(r'\D', '', valor)) < 6):
        raise forms.ValidationError('Ingresá un teléfono válido (solo números, espacios, guiones y +).')
    return valor


class BootstrapMixin:
    """Agrega las clases de Bootstrap a los widgets del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                clase = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = 'form-select'
            else:
                clase = 'form-control'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {clase}".strip()

    def full_clean(self):
        super().full_clean()
        # Marca en rojo los campos con error
        for nombre in self.errors:
            if nombre in self.fields:
                widget = self.fields[nombre].widget
                widget.attrs['class'] = f"{widget.attrs.get('class', '')} is-invalid".strip()


class RegistroForm(BootstrapMixin, forms.ModelForm):
    password1 = forms.CharField(label='Contraseña', strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                                help_text=password_validation.password_validators_help_text_html())
    password2 = forms.CharField(label='Repetir contraseña', strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'apellido', 'telefono']
        widgets = {'email': forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True})}

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese email.')
        return email

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get('password1'), datos.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        elif p1:
            # Los validadores de Django comparan contra los datos del usuario (email, nombre...)
            usuario = Usuario(email=datos.get('email', ''), nombre=datos.get('nombre', ''),
                              apellido=datos.get('apellido', ''))
            try:
                password_validation.validate_password(p1, usuario)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Usuario.Rol.CLIENTE  # todo registro nuevo es Cliente
        usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario


class LoginForm(BootstrapMixin, AuthenticationForm):
    error_messages = {
        'invalid_login': 'Email o contraseña incorrectos.',
        'inactive': 'Esta cuenta está desactivada.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'
        self.fields['username'].widget = forms.EmailInput(
            attrs={'autofocus': True, 'autocomplete': 'email', 'class': 'form-control'}
        )


class PerfilForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'telefono']

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))


class CambiarPasswordForm(BootstrapMixin, PasswordChangeForm):
    pass


class UsuarioRolForm(BootstrapMixin, forms.ModelForm):
    """Gestión de usuarios (solo Administrador): rol y si la cuenta está activa."""

    class Meta:
        model = Usuario
        fields = ['rol', 'is_active']

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor

    def clean(self):
        datos = super().clean()
        # Un administrador no puede quitarse a sí mismo el rol ni desactivarse (se quedaría afuera)
        if self.editor and self.instance.pk == self.editor.pk:
            if datos.get('rol') != Usuario.Rol.ADMIN or not datos.get('is_active'):
                raise forms.ValidationError('No podés quitarte el rol de Administrador ni desactivar tu propia cuenta.')
        return datos


# ----- Formularios del admin de Django -----

class AdminUsuarioCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label='Repetir contraseña', widget=forms.PasswordInput, strip=False)

    class Meta:
        model = Usuario
        fields = ['email', 'nombre', 'apellido', 'telefono', 'rol']

    def clean_password2(self):
        p1, p2 = self.cleaned_data.get('password1'), self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        password_validation.validate_password(p2, self.instance)
        return p2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario


class AdminUsuarioChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label='Contraseña',
        help_text='Las contraseñas no se guardan en texto plano. '
                  'Se cambian con el formulario <a href="../password/">cambiar contraseña</a>.',
    )

    class Meta:
        model = Usuario
        fields = '__all__'
