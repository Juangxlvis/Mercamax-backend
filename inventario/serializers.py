# inventario/serializers.py
from rest_framework import serializers
from .models import Proveedor, Producto, CategoriaProducto
from django.db.models import Sum, F, ExpressionWrapper, DecimalField

class ProductoSerializer(serializers.ModelSerializer):
    # 1. Definimos los nuevos campos que no existen en el modelo.
    stock_total = serializers.IntegerField(read_only=True)
    costo_promedio_ponderado = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    costo_compra = serializers.DecimalField(max_digits=10, decimal_places=2,default=0)
    precio_venta = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = serializers.IntegerField(required=False, default=0)
    proveedor = serializers.PrimaryKeyRelatedField(queryset=Proveedor.objects.all(), required=True)
    categoria = serializers.PrimaryKeyRelatedField(queryset=CategoriaProducto.objects.all(), required=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)


    class Meta:
        model = Producto
        # 2. Añadimos los nuevos campos a la lista de 'fields'.
        fields = [
            'id', 'nombre', 'codigo_barras', 'descripcion', 
            'precio_venta', 'costo_compra', 'stock_minimo', 'categoria', 'categoria_nombre','proveedor',
            'stock_total', 'costo_promedio_ponderado' 
        ]

    def to_representation(self, instance):
        """
        Sobreescribimos este método para añadir los cálculos al obtener los datos.
        """
        # Obtenemos la representación base (campos del modelo)
        data = super().to_representation(instance)
        
        # Cálculo del Stock Total
        stock_total = instance.lotes.aggregate(
            total=Sum('stock_items__cantidad')
        )['total'] or 0
        
        # Cálculo del Costo Promedio Ponderado
        valor_total_inventario = instance.lotes.aggregate(
            total_valor=Sum(F('stock_items__cantidad') * F('costo_compra_lote'))
        )['total_valor'] or 0

        if stock_total > 0:
            costo_promedio = valor_total_inventario / stock_total
        else:
            costo_promedio = 0

        # Añadimos los datos calculados a la respuesta
        data['stock_total'] = stock_total
        data['costo_promedio_ponderado'] = round(costo_promedio, 2)
        
        return data

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'
        
class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ['id', 'nombre']