from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet, VentaViewSet, BuscarProductoVentaView

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'', VentaViewSet, basename='venta')

urlpatterns = [
    path('buscar-producto/', BuscarProductoVentaView.as_view(), name='buscar-producto'),
    path('', include(router.urls)),
]