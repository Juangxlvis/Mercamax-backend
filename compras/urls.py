# compras/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrdenDeCompraViewSet, FacturaProveedorViewSet

router = DefaultRouter()
router.register(r'ordenes', OrdenDeCompraViewSet, basename='ordenes')
router.register(r'facturas', FacturaProveedorViewSet, basename='facturas')

urlpatterns = [
    path('', include(router.urls)),
]