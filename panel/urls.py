from django.urls import path

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.InicioPanelView.as_view(), name='inicio'),
    path('reportes/', views.ReportesView.as_view(), name='reportes'),
]
