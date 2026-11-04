from django.urls import path

from . import views

app_name = 'pedidos'

urlpatterns = [
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('checkout/confirmar/', views.ConfirmarPedidoView.as_view(), name='confirmar'),
    path('mis-pedidos/', views.MisPedidosView.as_view(), name='mis_pedidos'),
    path('<int:pk>/', views.PedidoDetailView.as_view(), name='detalle'),

    path('gestion/', views.PedidoGestionListView.as_view(), name='gestion_lista'),
    path('<int:pk>/estado/', views.CambiarEstadoView.as_view(), name='cambiar_estado'),
]
