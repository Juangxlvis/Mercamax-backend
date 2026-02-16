# core/urls.py
from .views import NotificacionListView

urlpatterns = [
    path('notificaciones/', NotificacionListView.as_view(), name='lista-notificaciones'),
]