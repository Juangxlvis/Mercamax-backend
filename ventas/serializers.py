# ventas/serializers.py
from rest_framework import serializers
from .models import Cliente, Venta, DetalleVenta, Factura


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'


class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = ['id', 'numero_factura', 'fecha_emision']


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.SerializerMethodField()

    class Meta:
        model = DetalleVenta
        fields = [
            'id', 'producto_nombre', 'cantidad',
            'precio_unitario', 'porcentaje_iva',
            'subtotal', 'impuesto', 'total_linea'
        ]

    def get_producto_nombre(self, obj):
        try:
            return obj.stock_item.lote.producto.nombre
        except Exception:
            return '—'


class VentaSerializer(serializers.ModelSerializer):
    cajero_nombre = serializers.SerializerMethodField()
    cliente_nombre = serializers.SerializerMethodField()
    factura = FacturaSerializer(read_only=True)
    detalles = DetalleVentaSerializer(source='detalleventa_set', many=True, read_only=True)
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id', 'cajero_nombre', 'cliente_nombre',
            'fecha_hora', 'estado',
            'metodo_pago', 'metodo_pago_display',
            'subtotal', 'total_impuestos', 'total',
            'notas', 'factura', 'detalles'
        ]

    def get_cajero_nombre(self, obj):
        return obj.cajero.get_full_name() or obj.cajero.username

    def get_cliente_nombre(self, obj):
        return obj.cliente.nombre if obj.cliente else None


class ItemVentaSerializer(serializers.Serializer):
    """Serializer para cada ítem del carrito enviado por el frontend."""
    stock_item_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)


class VentaCreateSerializer(serializers.Serializer):
    """Serializer para el payload completo de creación de venta."""
    cliente_id = serializers.IntegerField(required=False, allow_null=True)
    metodo_pago = serializers.ChoiceField(
        choices=['EFECTIVO', 'TARJETA_CREDITO', 'TARJETA_DEBITO', 'TRANSFERENCIA'],
        default='EFECTIVO'
    )
    notas = serializers.CharField(required=False, allow_blank=True, default='')
    items = ItemVentaSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debes incluir al menos un producto.")
        return value