from django.urls import path

from . import views

app_name = 'carrito'

urlpatterns = [
    path('', views.CarritoView.as_view(), name='ver'),
    path('agregar/<int:producto_id>/', views.AgregarView.as_view(), name='agregar'),
    path('actualizar/<int:producto_id>/', views.ActualizarView.as_view(), name='actualizar'),
    path('quitar/<int:producto_id>/', views.QuitarView.as_view(), name='quitar'),
    path('vaciar/', views.VaciarView.as_view(), name='vaciar'),
]
