# inventario/views.py
from rest_framework import viewsets, generics
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Proveedor, Producto
from .serializers import ProveedorSerializer, ProductoSerializer, CategoriaProducto, CategoriaProductoSerializer
from bodega.models import StockItem # Importamos StockItem
from bodega.serializers import StockDetailSerializer
from django.db.models import Sum, F
from ventas.models import DetalleVenta
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
import traceback
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny


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
@permission_classes([AllowAny])
def inventario_estadisticas(request):
    try:
        productos = Producto.objects.all()
        
        total_valor_stock = 0
        total_costo_stock = 0
        total_productos = 0
        
        for producto in productos:
            # Traemos las propiedades calculadas (el @property de tu modelo)
            stock = producto.stock_total or 0
            costo = float(producto.costo_promedio_ponderado or 0)
            precio = float(producto.precio_venta or 0)
            
            # Sumamos a los totales
            total_productos += stock
            total_valor_stock += stock * precio
            total_costo_stock += stock * costo
            
        total_ganancia = total_valor_stock - total_costo_stock

        return Response({
            "valor_en_stock": round(total_valor_stock, 2),
            "costo_de_stock": round(total_costo_stock, 2),
            "ganancia_estimada": round(total_ganancia, 2),
            "total_productos": total_productos
        })
        
    except Exception as e:
        import traceback
        return Response({
            "error": "Hubo un problema al calcular las estadísticas.",
            "detalle": str(e),
            "pista": traceback.format_exc()
        }, status=500)


class ReporteRotacionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            dias = int(request.query_params.get('dias', 30))
            fecha_inicio = timezone.now() - timedelta(days=dias)

            valor_inventario_actual = StockItem.objects.aggregate(
                total=Sum(F('cantidad') * F('lote__costo_compra_lote'))
            )['total'] or 1 

            
            detalles = DetalleVenta.objects.filter(venta__fecha_hora__gte=fecha_inicio).select_related('producto')
            
            cogs = 0
            for detalle in detalles:
                costo_unitario = getattr(detalle.producto, 'costo_promedio_ponderado', 0)
                cogs += detalle.cantidad * float(costo_unitario)

            rotacion = float(cogs) / float(valor_inventario_actual)
            
            dias_inventario = 0
            if rotacion > 0:
                dias_inventario = dias / rotacion

            return Response({
                "periodo_dias": dias,
                "valor_inventario_promedio": round(valor_inventario_actual, 2),
                "costo_ventas_cogs": round(cogs, 2),
                "tasa_rotacion": round(rotacion, 2),
                "dias_promedio_venta": round(dias_inventario, 1),
                "mensaje": self._interpretar_kpi(rotacion)
            })

        except Exception as e:
            import traceback
            return Response({
                "ERROR_DETECTADO": str(e),
                "PISTA_EXACTA": traceback.format_exc()
            }, status=400)

    def _interpretar_kpi(self, rotacion):
        if rotacion < 1:
            return "Peligro: El inventario está estancado."
        elif rotacion < 3:
            return "Aceptable: Rotación normal."
        return "Excelente: El inventario se mueve rápido."