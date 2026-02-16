# inventario/views.py
from rest_framework import viewsets, generics
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Proveedor, Producto
from .serializers import ProveedorSerializer, ProductoSerializer, CategoriaProducto, CategoriaProductoSerializer
from bodega.models import StockItem # Importamos StockItem
from bodega.serializers import StockDetailSerializer
from django.db.models import Sum, F


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class CategoriaProductoListView(generics.ListAPIView):
    queryset = CategoriaProducto.objects.all()
    serializer_class = CategoriaProductoSerializer

    # --- NUEVA ACCIÓN PERSONALIZADA ---
    @action(detail=True, methods=['get'], url_path='stock-details')
    def stock_details(self, request, pk=None):
        """
        Endpoint para devolver la distribución detallada del stock
        de un producto específico en todas las ubicaciones.
        """
        # Buscamos el producto por su ID (pk)
        producto = self.get_object()
        
        # Buscamos todos los StockItems que pertenecen a los lotes de este producto
        queryset = StockItem.objects.filter(lote__producto=producto).order_by('ubicacion__nombre')
        
        # Usamos nuestro nuevo serializer para formatear los datos
        serializer = StockDetailSerializer(queryset, many=True)
        
        return Response(serializer.data)
    
@api_view(['GET'])
def inventario_estadisticas(request):
    stats = Producto.objects.aggregate(
        total_valor_stock=Sum(F('stock') * F('precio_venta')),
        total_costo_stock=Sum(F('stock') * F('costo_compra')),
        total_ganancia=Sum(F('stock') * (F('precio_venta') - F('costo_compra'))),
        total_productos=Sum(F('stock'))
    )

    return Response({
        "valor_en_stock": stats['total_valor_stock'] or 0,
        "costo_de_stock": stats['total_costo_stock'] or 0,
        "ganancia_estimada": stats['total_ganancia'] or 0,
        "total_productos": stats['total_productos'] or 0
    })