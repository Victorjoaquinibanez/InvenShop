from django.urls import path

from . import views

app_name = 'catalogo'

urlpatterns = [
    path('', views.ProductoListView.as_view(), name='lista'),
    path('producto/<slug:slug>/', views.ProductoDetailView.as_view(), name='detalle'),

    # Panel de gestión
    path('gestion/productos/', views.ProductoGestionListView.as_view(), name='gestion_productos'),
    path('gestion/productos/nuevo/', views.ProductoCreateView.as_view(), name='producto_crear'),
    path('gestion/productos/<int:pk>/editar/', views.ProductoUpdateView.as_view(), name='producto_editar'),
    path('gestion/productos/<int:pk>/eliminar/', views.ProductoDeleteView.as_view(), name='producto_eliminar'),
    path('gestion/productos/<int:pk>/stock/', views.ajustar_stock, name='producto_stock'),
    path('gestion/productos/<int:pk>/activo/', views.alternar_activo, name='producto_activo'),

    path('gestion/categorias/', views.CategoriaListView.as_view(), name='gestion_categorias'),
    path('gestion/categorias/nueva/', views.CategoriaCreateView.as_view(), name='categoria_crear'),
    path('gestion/categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_editar'),
    path('gestion/categorias/<int:pk>/eliminar/', views.CategoriaDeleteView.as_view(), name='categoria_eliminar'),
]
