# inventario/serializers.py
from rest_framework import serializers
from .models import Proveedor, Producto, CategoriaProducto
from django.db.models import Sum, F, ExpressionWrapper, DecimalField

class ProductoSerializer(serializers.ModelSerializer):
    # 1. Como la lógica matemática ya vive en los @property del models.py, 
    # aquí solo le decimos a Django: "Léelos y ponlos en el JSON".
    stock_total = serializers.ReadOnlyField()
    costo_promedio_ponderado = serializers.ReadOnlyField()
    costo_compra = serializers.ReadOnlyField() # <-- ¡Aquí está nuestro nuevo campo!
    porcentaje_iva = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0.00)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Producto
        # 2. Añadimos todos los campos que queremos mostrar
        fields = [
            'id', 'nombre', 'codigo_barras', 'descripcion', 
            'precio_venta', 'costo_compra', 'stock_minimo', 'categoria', 'categoria_nombre','proveedor',
            'stock_total', 'costo_promedio_ponderado', 'porcentaje_iva' 
        ]

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'
        
class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ['id', 'nombre']