from django.shortcuts import render
from rest_framework.views import APIView
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from ventas.models import DetalleVenta #Necesitamos importar datos de ventas
from inventario.models import Producto
from rest_framework.response import Response
from rest_framework import status

from rest_framework import viewsets
from .models import CategoriaUbicacion, Ubicacion, Lote, StockItem, AjusteInventario
from .serializers import (
    CategoriaUbicacionSerializer, UbicacionSerializer, 
    LoteSerializer, StockItemSerializer
)

class LowStockAlertView(APIView):
    """
    Devuelve una lista de productos cuyo stock total actual
    es menor o igual a su punto de reorden (stock_minimo).
    """
    def get(self, request, *args, **kwargs):
        # Usamos 'annotate' para calcular la suma del campo 'cantidad' de todos los StockItem relacionados
        productos_con_stock = Producto.objects.annotate(
            stock_total=Sum('lotes__stock_items__cantidad')
        )
        
        # Filtramos los productos donde el stock_total es menor o igual al stock_minimo
        productos_en_alerta = productos_con_stock.filter(
            stock_total__lte=models.F('stock_minimo')
        )

        # Preparamos los datos para la respuesta
        data = [
            {
                'id': producto.id,
                'nombre': producto.nombre,
                'stock_minimo': producto.stock_minimo,
                'stock_total': producto.stock_total,
                'mensaje': f"¡Stock bajo! Quedan {producto.stock_total} de un mínimo de {producto.stock_minimo}."
            }
            for producto in productos_en_alerta
        ]
        
        return Response(data)

class ExpiringLotsAlertView(APIView):
    """
    Devuelve una lista de lotes que están próximos a vencer.
    Por defecto, se consideran los próximos 30 días.
    """
    def get(self, request, *args, **kwargs):
        # Calculamos la fecha límite (hoy + 30 días)
        fecha_limite = timezone.now().date() + timedelta(days=30)
        
        # Buscamos lotes cuya fecha de caducidad sea anterior o igual a la fecha límite y que aún tengan stock
        lotes_por_vencer = Lote.objects.annotate(
            stock_total_lote=Sum('stock_items__cantidad')
        ).filter(
            fecha_caducidad__lte=fecha_limite,
            stock_total_lote__gt=0
        ).order_by('fecha_caducidad')

        # Preparamos los datos para la respuesta
        data = [
            {
                'id_lote': lote.id,
                'codigo_lote': lote.codigo_lote,
                'producto_nombre': lote.producto.nombre,
                'fecha_caducidad': lote.fecha_caducidad,
                'stock_restante_lote': lote.stock_total_lote,
                'dias_para_vencer': (lote.fecha_caducidad - timezone.now().date()).days
            }
            for lote in lotes_por_vencer
        ]

        return Response(data)
    
class StockValuationReportView(APIView):
    """
    Calcula y devuelve el valor total del inventario actual
    basado en el costo promedio ponderado de cada producto.
    """
    def get(self, request, *args, **kwargs):
        productos = Producto.objects.annotate(
            # Suma la cantidad total de cada producto en stock
            stock_total=Sum('lotes__stock_items__cantidad'),
            # Calcula el valor total de cada lote (cantidad * costo_lote)
            valor_lote=ExpressionWrapper(
                F('lotes__stock_items__cantidad') * F('lotes__costo_compra_lote'),
                output_field=DecimalField()
            )
        ).annotate(
            # Suma el valor de todos los lotes para obtener el valor total del producto
            valor_total_producto=Sum('valor_lote')
        ).filter(stock_total__gt=0) # Solo productos con stock

        report_data = []
        valor_total_inventario = 0

        for producto in productos:
            costo_promedio = producto.valor_total_producto / producto.stock_total
            valor_total_inventario += producto.valor_total_producto
            report_data.append({
                'producto_id': producto.id,
                'producto_nombre': producto.nombre,
                'stock_total': producto.stock_total,
                'costo_promedio_ponderado': round(costo_promedio, 2),
                'valor_total_producto': round(producto.valor_total_producto, 2)
            })

        return Response({
            'valor_total_inventario': round(valor_total_inventario, 2),
            'detalle_productos': report_data
        })

class InventoryTurnoverReportView(APIView):
    """
    Calcula la rotación de inventario en un periodo de tiempo.
    Métrica: Costo de Ventas / Inventario Promedio
    """
    def get(self, request, *args, **kwargs):
        # Para este ejemplo, calcularemos para los últimos 365 días
        end_date = timezone.now()
        start_date = end_date - timedelta(days=365)

        # 1. Calcular el Costo de Ventas (COGS) en el periodo
        # Asumimos que DetalleVenta guarda el costo al momento de la venta.
        # Si no, necesitaríamos un modelo de Historial de Costos.
        # Por simplicidad, usaremos el 'subtotal' como aproximación.
        cost_of_goods_sold = DetalleVenta.objects.filter(
            venta__fecha_hora__range=(start_date, end_date)
        ).aggregate(total_cogs=Sum('subtotal'))['total_cogs'] or 0

        # 2. Calcular el Inventario Promedio
        # (Inventario Inicial + Inventario Final) / 2
        # Este es un cálculo complejo, por ahora usaremos el valor actual como aproximación
        valor_inventario_actual = StockValuationReportView().get(request).data['valor_total_inventario']
        
        # El inventario inicial sería una consulta a una fecha anterior.
        # Por simplicidad, asumiremos que es similar al actual.
        inventario_promedio = valor_inventario_actual # Simplificación

        # 3. Calcular Rotación
        if inventario_promedio > 0:
            rotacion = cost_of_goods_sold / inventario_promedio
        else:
            rotacion = 0

        return Response({
            'periodo_inicio': start_date.date(),
            'periodo_fin': end_date.date(),
            'costo_de_ventas': round(cost_of_goods_sold, 2),
            'inventario_promedio_estimado': round(inventario_promedio, 2),
            'rotacion_de_inventario': round(rotacion, 2),
            'objetivo_metrica': ">= 6 veces/año" # Métrica del Plan de Calidad
        })


class CreateInventoryAdjustmentView(APIView):
    """
    Endpoint para crear un ajuste de inventario.
    Recibe el ID del StockItem, la cantidad contada y el motivo.
    """
    # Aquí deberías añadir una clase de permiso para Encargado de Inventario
    
    def post(self, request, *args, **kwargs):
        stock_item_id = request.data.get('stock_item_id')
        cantidad_contada = request.data.get('cantidad_contada')
        motivo = request.data.get('motivo')
        notas = request.data.get('notas', '')

        try:
            stock_item = StockItem.objects.get(id=stock_item_id)
            cantidad_anterior = stock_item.cantidad
            
            # Actualizar el stock
            stock_item.cantidad = cantidad_contada
            stock_item.save()

            # Crear el registro de auditoría
            AjusteInventario.objects.create(
                stock_item=stock_item,
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=cantidad_contada,
                motivo=motivo,
                notas=notas,
                usuario=request.user
            )
            
            return Response(
                {'detail': 'Ajuste de inventario realizado con éxito.'}, 
                status=status.HTTP_200_OK
            )
        except StockItem.DoesNotExist:
            return Response({'error': 'El ítem de stock no existe.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CategoriaUbicacionViewSet(viewsets.ModelViewSet):
    queryset = CategoriaUbicacion.objects.all()
    serializer_class = CategoriaUbicacionSerializer

class UbicacionViewSet(viewsets.ModelViewSet):
    queryset = Ubicacion.objects.all()
    serializer_class = UbicacionSerializer

class LoteViewSet(viewsets.ModelViewSet):
    queryset = Lote.objects.all()
    serializer_class = LoteSerializer

class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer

class TipoUbicacionView(APIView):
    """
    Devuelve la lista de tipos de ubicación disponibles desde el modelo Ubicacion.
    """
    def get(self, request, *args, **kwargs):
        tipos = [
            {"value": choice[0], "label": choice[1]}
            for choice in Ubicacion.TipoUbicacion.choices
        ]
        return Response(tipos, status=status.HTTP_200_OK)