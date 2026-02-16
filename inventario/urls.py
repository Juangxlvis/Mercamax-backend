# inventario/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet, ProductoViewSet, CategoriaProductoListView, inventario_estadisticas

router = DefaultRouter()
router.register(r'proveedores', ProveedorViewSet)
router.register(r'productos', ProductoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('categorias/', CategoriaProductoListView.as_view(), name='categorias-list'),
    path('estadisticas/', inventario_estadisticas, name='inventario-estadisticas'),
]