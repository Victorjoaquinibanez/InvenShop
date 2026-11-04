from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

if settings.DEBUG:
    # En desarrollo Django sirve las imágenes subidas; en producción lo hace el servidor web
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
