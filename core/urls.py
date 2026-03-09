# core/urls.py
from .views import NotificacionListView
from django.urls import path
from .views import NotificacionListView, MarcarTodasLeidasView

urlpatterns = [
    path('notificaciones/', NotificacionListView.as_view(), name='lista-notificaciones'),
    path('notificaciones/marcar-todas-leidas/', MarcarTodasLeidasView.as_view(), name='marcar-leidas'),
]

