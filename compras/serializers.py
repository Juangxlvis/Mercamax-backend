# compras/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    OrdenDeCompra, DetalleOrdenDeCompra,
    RecepcionMercancia, DetalleRecepcion,
    FacturaProveedor, PagoProveedor
)


# ── Detalles ─────────────────────────────────────────────────────────────────

class DetalleOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(
        source='producto.nombre', read_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = DetalleOrdenDeCompra
        fields = [
            'id', 'producto', 'producto_nombre',
            'cantidad_solicitada', 'cantidad_recibida',
            'costo_unitario', 'subtotal'
        ]
    
    def get_subtotal(self, obj):
        try:
            return float(obj.cantidad_solicitada * obj.costo_unitario)
        except Exception:
            return 0


class DetalleOrdenCreateSerializer(serializers.Serializer):
    producto = serializers.IntegerField()
    cantidad_solicitada = serializers.IntegerField(min_value=1)
    costo_unitario = serializers.DecimalField(max_digits=10, decimal_places=2)


# ── Orden de Compra ───────────────────────────────────────────────────────────

class OrdenDeCompraSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(
        source='proveedor.nombre', read_only=True
    )
    creado_por_nombre = serializers.SerializerMethodField()
    aprobado_por_nombre = serializers.SerializerMethodField()
    tiene_factura = serializers.SerializerMethodField()
    detalles = DetalleOrdenSerializer(many=True, read_only=True)
    estado_pago = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    numero_orden = serializers.CharField(read_only=True)

    class Meta:
        model = OrdenDeCompra
        fields = [
            'id', 'numero_orden', 'proveedor', 'proveedor_nombre',
            'creado_por_nombre', 'aprobado_por_nombre',
            'fecha_creacion', 'fecha_estimada_entrega',
            'fecha_aprobacion', 'fecha_recepcion',
            'estado', 'motivo_rechazo', 'notas',
            'total', 'detalles', 'tiene_factura', 'estado_pago'
        ]

    def get_total(self, obj):
        try:
            return float(sum(
                d.cantidad_solicitada * d.costo_unitario
                for d in obj.detalles.all()
            ))
        except Exception:
            return 0
    
    def get_estado_pago(self, obj):
        if hasattr(obj, 'factura_proveedor'):
            return obj.factura_proveedor.estado
        return None

    def get_tiene_factura(self, obj):
        return hasattr(obj, 'factura_proveedor')

    def get_creado_por_nombre(self, obj):
        if obj.creado_por:
            return obj.creado_por.get_full_name() or obj.creado_por.username
        return None

    def get_aprobado_por_nombre(self, obj):
        if obj.aprobado_por:
            return obj.aprobado_por.get_full_name() or obj.aprobado_por.username
        return None


class OrdenDeCompraCreateSerializer(serializers.Serializer):
    proveedor = serializers.IntegerField()
    fecha_estimada_entrega = serializers.DateField()
    notas = serializers.CharField(required=False, allow_blank=True, default='')
    detalles = DetalleOrdenCreateSerializer(many=True)

    def validate_fecha_estimada_entrega(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "La fecha estimada de entrega debe ser igual o posterior a hoy."
            )
        return value

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError(
                "La orden debe incluir al menos un producto."
            )
        return value


class AprobarRechazarSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=['APROBAR', 'RECHAZAR'])
    motivo_rechazo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['accion'] == 'RECHAZAR' and not data.get('motivo_rechazo'):
            raise serializers.ValidationError(
                "El motivo de rechazo es obligatorio al rechazar una orden."
            )
        return data


# ── Recepción ─────────────────────────────────────────────────────────────────

class DetalleRecepcionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(
        source='detalle_orden.producto.nombre', read_only=True
    )
    cantidad_solicitada = serializers.IntegerField(
        source='detalle_orden.cantidad_solicitada', read_only=True
    )

    class Meta:
        model = DetalleRecepcion
        fields = [
            'id', 'detalle_orden', 'producto_nombre',
            'cantidad_solicitada', 'cantidad_recibida',
            'estado', 'observacion'
        ]


class DetalleRecepcionCreateSerializer(serializers.Serializer):
    detalle_orden_id = serializers.IntegerField()
    cantidad_recibida = serializers.IntegerField(min_value=0)
    estado = serializers.ChoiceField(choices=['CONFORME', 'NO_CONFORME'])
    observacion = serializers.CharField(required=False, allow_blank=True)
    fecha_caducidad = serializers.DateField(required=False, allow_null=True)
    
    def validate(self, data):
        if data['estado'] == 'NO_CONFORME' and not data.get('observacion'):
            raise serializers.ValidationError(
                "La observación es obligatoria para productos no conformes."
            )
        return data


class RecepcionMercanciaSerializer(serializers.ModelSerializer):
    recibido_por_nombre = serializers.SerializerMethodField()
    detalles = DetalleRecepcionSerializer(many=True, read_only=True)

    class Meta:
        model = RecepcionMercancia
        fields = [
            'id', 'orden', 'recibido_por_nombre',
            'fecha_recepcion', 'factura_proveedor', 'notas', 'detalles'
        ]

    def get_recibido_por_nombre(self, obj):
        return obj.recibido_por.get_full_name() or obj.recibido_por.username


class RecepcionCreateSerializer(serializers.Serializer):
    factura_proveedor = serializers.CharField(required=False, allow_blank=True)
    notas = serializers.CharField(required=False, allow_blank=True)
    detalles = DetalleRecepcionCreateSerializer(many=True)

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError(
                "Debe incluir al menos un producto en la recepción."
            )
        return value


# ── Factura y Pagos ───────────────────────────────────────────────────────────

class PagoProveedorSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = PagoProveedor
        fields = [
            'id', 'fecha_pago', 'monto', 'metodo_pago',
            'numero_comprobante', 'notas', 'registrado_por_nombre'
        ]

    def get_registrado_por_nombre(self, obj):
        return obj.registrado_por.get_full_name() or obj.registrado_por.username


class FacturaProveedorSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(
        source='orden.proveedor.nombre', read_only=True
    )
    monto_pendiente = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    pagos = PagoProveedorSerializer(many=True, read_only=True)

    class Meta:
        model = FacturaProveedor
        fields = [
            'id', 'orden', 'proveedor_nombre', 'numero_factura',
            'fecha_emision', 'fecha_vencimiento',
            'monto_total', 'monto_pagado', 'monto_pendiente',
            'estado', 'pagos'
        ]


class FacturaCreateSerializer(serializers.Serializer):
    numero_factura = serializers.CharField(required=False, allow_blank=True, default='')
    fecha_emision = serializers.DateField()
    fecha_vencimiento = serializers.DateField(required=False)
    monto_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class PagoCreateSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = serializers.ChoiceField(
        choices=['EFECTIVO', 'TRANSFERENCIA', 'CHEQUE']
    )
    numero_comprobante = serializers.CharField()
    notas = serializers.CharField(required=False, allow_blank=True)