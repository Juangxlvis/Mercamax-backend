# bodega/serializers.py
from rest_framework import serializers
from .models import CategoriaUbicacion, Ubicacion, Lote, StockItem
from django.db.models import Sum, F

class CategoriaUbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaUbicacion
        fields = '__all__'

class UbicacionSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    parent_nombre = serializers.CharField(source='parent.nombre', read_only=True)
    class Meta:
        model = Ubicacion
        fields = '__all__'
    
    def validate_tipo(self, value):
        if not value:
            raise serializers.ValidationError("El tipo de ubicación es obligatorio.")
        return value

    def validate_nombre(self, value):
        if not value:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return value

class LoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = '__all__'

class StockItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockItem
        fields = '__all__'

    def validate(self, data):
        """
        Verifica que la categoría del producto coincida con la categoría de la ubicación.
        """
        lote = data.get('lote')
        ubicacion = data.get('ubicacion')
        cantidad_a_anadir = data.get('cantidad')

        if ubicacion.capacidad_maxima is not None:
            # 1. Calculamos cuánto stock hay actualmente en esa ubicación
            stock_actual_agregado = StockItem.objects.filter(
                ubicacion=ubicacion
            ).aggregate(total=Sum('cantidad'))

            stock_actual = stock_actual_agregado.get('total', 0) # <-- CAMBIO CLAVE AQUÍ

            # 2. Calculamos cuál sería el nuevo total
            nuevo_total = stock_actual + cantidad_a_anadir

            if self.instance: # Si estamos actualizando un StockItem existente
                nuevo_total -= self.instance.cantidad

            # 3. Comparamos y lanzamos el error si se excede
            if nuevo_total > ubicacion.capacidad_maxima:
                espacio_disponible = ubicacion.capacidad_maxima - stock_actual
                espacio_disponible_para_mensaje = max(0, ubicacion.capacidad_maxima - stock_actual)
                
                raise serializers.ValidationError(
                    f"Se excede la capacidad del estante '{ubicacion.nombre}'. "
                    f"Intenta añadir {cantidad_a_anadir} unidades pero solo hay espacio para {espacio_disponible_para_mensaje}."
                )

        if ubicacion.tipo == 'BODEGA':
            raise serializers.ValidationError(
                "Error de validación: No se puede asignar stock a una bodega general. "
                "Por favor, seleccione un estante específico."
            )

        # Obtenemos la categoría del producto a través del lote
        categoria_producto = lote.producto.categoria
        # Obtenemos la categoría de la ubicación
        categoria_ubicacion = ubicacion.categoria

        # VALIDACIÓN MEJORADA: Si el estante espera una categoría, el producto DEBE tener una.
        if categoria_ubicacion and not categoria_producto:
            raise serializers.ValidationError(
                f"La ubicación '{ubicacion.nombre}' es solo para productos de categoría '{categoria_ubicacion}', "
                f"pero el producto '{lote.producto.nombre}' no tiene una categoría asignada."
            )
        
        # Comparamos si ambas existen y si son diferentes
        if categoria_producto and categoria_ubicacion and categoria_producto.nombre != categoria_ubicacion.nombre:
            raise serializers.ValidationError(
                f"Error de validación: No se puede colocar un producto de categoría '{categoria_producto}' en una ubicación de categoría '{categoria_ubicacion}'."
            )

        return data

class StockDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para mostrar el detalle del stock de un producto,
    incluyendo información de la ubicación y el lote.
    """
    # Usamos 'source' para acceder a los datos de los modelos relacionados
    ubicacion_nombre = serializers.CharField(source='ubicacion.nombre', read_only=True)
    lote_codigo = serializers.CharField(source='lote.codigo_lote', read_only=True)
    fecha_caducidad = serializers.DateField(source='lote.fecha_caducidad', read_only=True)

    class Meta:
        model = StockItem
        # Especificamos los campos que queremos mostrar
        fields = ['ubicacion_nombre', 'lote_codigo', 'fecha_caducidad', 'cantidad']
