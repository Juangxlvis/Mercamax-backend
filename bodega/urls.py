# bodega/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaUbicacionViewSet, UbicacionViewSet, TipoUbicacionView, LoteViewSet, StockItemViewSet, LowStockAlertView, ExpiringLotsAlertView, StockValuationReportView, InventoryTurnoverReportView, CreateInventoryAdjustmentView

router = DefaultRouter()
router.register(r'categorias-ubicacion', CategoriaUbicacionViewSet, basename='categoria-ubicacion')
router.register(r'ubicaciones', UbicacionViewSet, basename='ubicacion')
router.register(r'lotes', LoteViewSet, basename='lote')
router.register(r'stockitems', StockItemViewSet, basename='stockitem')

urlpatterns = [
    path('', include(router.urls)),
    #Nuevas rutas para alertas!!!:
    path('alerts/low-stock/', LowStockAlertView.as_view(), name='low-stock-alert'),
    path('alerts/expiring-lots/', ExpiringLotsAlertView.as_view(), name='expiring-lots-alert'),
    #Nuevas rutas para los reportes:
    path('reports/stock-valuation/', StockValuationReportView.as_view(), name='stock-valuation-report'),
    path('reports/inventory-turnover/', InventoryTurnoverReportView.as_view(), name='inventory-turnover-report'),
    path('inventory/adjust/', CreateInventoryAdjustmentView.as_view(), name='create-inventory-adjustment'),
    path('tipos-ubicacion/', TipoUbicacionView.as_view(), name='tipos-ubicacion'),

]