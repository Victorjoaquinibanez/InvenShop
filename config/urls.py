from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = 'InvenShop · Administración'
admin.site.site_title = 'InvenShop'
admin.site.index_title = 'Gestión de la tienda'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuenta/', include('usuarios.urls')),
    path('carrito/', include('carrito.urls')),
    path('pedidos/', include('pedidos.urls')),
    path('panel/', include('panel.urls')),
    path('', include('catalogo.urls')),
]

if settings.SERVIR_MEDIA:
    # En desarrollo Django sirve las imágenes subidas; en producción lo hace el servidor web
    urlpatterns += [
        re_path(rf'^{settings.MEDIA_URL.lstrip("/")}(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
