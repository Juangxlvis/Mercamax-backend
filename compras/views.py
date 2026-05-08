# compras/views.py
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from bodega.models import Lote
import datetime

from .models import (
    OrdenDeCompra, DetalleOrdenDeCompra,
    RecepcionMercancia, DetalleRecepcion,
    FacturaProveedor, PagoProveedor
)
from inventario.models import Producto
from bodega.models import Lote, StockItem
from .serializers import (
    OrdenDeCompraSerializer, OrdenDeCompraCreateSerializer,
    AprobarRechazarSerializer, RecepcionMercanciaSerializer,
    RecepcionCreateSerializer, FacturaProveedorSerializer,
    FacturaCreateSerializer, PagoCreateSerializer
)


class OrdenDeCompraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    RF-P01: Registro de órdenes de compra
    RF-P02: Aprobación/rechazo de órdenes
    RF-P03: Recepción de mercancía
    """
    queryset = OrdenDeCompra.objects.select_related(
        'proveedor', 'creado_por', 'aprobado_por'
    ).prefetch_related('detalles__producto').all()
    serializer_class = OrdenDeCompraSerializer
    permission_classes = [IsAuthenticated]

    # ── RF-P01: Crear orden ─────────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='crear')
    def crear_orden(self, request):
        serializer = OrdenDeCompraCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        try:
            with transaction.atomic():
                # Validar proveedor activo
                from inventario.models import Proveedor
                try:
                    proveedor = Proveedor.objects.get(id=datos['proveedor'])
                except Proveedor.DoesNotExist:
                    return Response(
                        {"error": "El proveedor no existe."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                orden = OrdenDeCompra.objects.create(
                    proveedor=proveedor,
                    creado_por=request.user,
                    fecha_estimada_entrega=datos['fecha_estimada_entrega'],
                    notas=datos.get('notas', ''),
                    estado='PENDIENTE'
                )

                for item in datos['detalles']:
                    try:
                        producto = Producto.objects.get(id=item['producto'])
                    except Producto.DoesNotExist:
                        raise ValueError(f"Producto con ID {item['producto']} no existe.")

                    DetalleOrdenDeCompra.objects.create(
                        orden=orden,
                        producto=producto,
                        cantidad_solicitada=item['cantidad_solicitada'],
                        costo_unitario=item['costo_unitario']
                    )

            orden_creada = OrdenDeCompra.objects.prefetch_related(
                'detalles__producto'
            ).get(id=orden.id)
            return Response(
                OrdenDeCompraSerializer(orden_creada).data,
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ── RF-P02: Aprobar o rechazar ──────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='aprobar-rechazar')
    def aprobar_rechazar(self, request, pk=None):
        orden = self.get_object()

        if orden.estado != 'PENDIENTE':
            return Response(
                {"error": f"Solo se pueden aprobar órdenes en estado PENDIENTE. Estado actual: {orden.estado}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AprobarRechazarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        if datos['accion'] == 'APROBAR':
            orden.estado = 'APROBADA'
            orden.aprobado_por = request.user
            orden.fecha_aprobacion = timezone.now()
            orden.motivo_rechazo = None
        else:
            orden.estado = 'RECHAZADA'
            orden.aprobado_por = request.user
            orden.fecha_aprobacion = timezone.now()
            orden.motivo_rechazo = datos['motivo_rechazo']

        orden.save()
        return Response(OrdenDeCompraSerializer(orden).data)

    # ── RF-P03: Registrar recepción ─────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='recepcionar')
    def recepcionar(self, request, pk=None):
        orden = self.get_object()

        if hasattr(orden, 'factura_proveedor'):
            return Response(
                {"error": "Esta orden ya tiene una factura registrada. No se puede recepcionar más mercancía."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if orden.estado not in ['APROBADA', 'PARCIAL']:
            return Response(
                {"error": "Solo se puede recepcionar una orden APROBADA o con recepción PARCIAL."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RecepcionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        try:
            with transaction.atomic():
                recepcion = RecepcionMercancia.objects.create(
                    orden=orden,
                    recibido_por=request.user,
                    factura_proveedor=datos.get('factura_proveedor', ''),
                    notas=datos.get('notas', '')
                )

                for item in datos['detalles']:
                    try:
                        detalle_orden = DetalleOrdenDeCompra.objects.get(
                            id=item['detalle_orden_id'],
                            orden=orden
                        )
                    except DetalleOrdenDeCompra.DoesNotExist:
                        raise ValueError(
                            f"El detalle con ID {item['detalle_orden_id']} no pertenece a esta orden."
                        )

                    DetalleRecepcion.objects.create(
                        recepcion=recepcion,
                        detalle_orden=detalle_orden,
                        cantidad_recibida=item['cantidad_recibida'],
                        estado=item['estado'],
                        observacion=item.get('observacion', '')
                    )

                    # RF-P04: Actualizar stock solo si es conforme
                    if item['estado'] == 'CONFORME' and item['cantidad_recibida'] > 0:
                        nueva_cantidad = detalle_orden.cantidad_recibida + item['cantidad_recibida']
                        if nueva_cantidad > detalle_orden.cantidad_solicitada:
                            raise ValueError(
                                f"La cantidad recibida para '{detalle_orden.producto.nombre}' "
                                f"({nueva_cantidad}) supera la cantidad solicitada "
                                f"({detalle_orden.cantidad_solicitada})."
                            )
                        detalle_orden.cantidad_recibida = nueva_cantidad
                        detalle_orden.save()
                        self._actualizar_stock(
                            orden, detalle_orden, item['cantidad_recibida'], 
                            request.user,
                            fecha_caducidad=item.get('fecha_caducidad')
                        )

                # Actualizar estado de la orden
                orden.fecha_recepcion = timezone.now()
                orden.save()

                # Recargar detalles frescos desde la BD
                from django.db.models import Sum
                detalles_actualizados = DetalleOrdenDeCompra.objects.filter(orden=orden)
                todos_recibidos = all(
                    d.cantidad_recibida >= d.cantidad_solicitada 
                    for d in detalles_actualizados
                )
                orden.estado = 'RECIBIDA' if todos_recibidos else 'PARCIAL'
                orden.save()

            return Response(
                RecepcionMercanciaSerializer(recepcion).data,
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _actualizar_stock(self, orden, detalle_orden, cantidad, usuario, fecha_caducidad=None):
        

        producto = detalle_orden.producto
        codigo = f"LOT-OC{orden.id:06d}-P{producto.id}"

        lote, creado = Lote.objects.get_or_create(
            codigo_lote=codigo,
            defaults={
                'producto': producto,
                'proveedor': orden.proveedor,
                'cantidad_inicial': 0,
                'costo_unitario': detalle_orden.costo_unitario,
                'fecha_caducidad': fecha_caducidad or datetime.date.today().replace(
                    year=datetime.date.today().year + 1
                ),
            }
        )

        lote.cantidad_inicial += cantidad
        lote.save()


class FacturaProveedorViewSet(viewsets.ReadOnlyModelViewSet):
    """RF-P05: Gestión de pagos a proveedores"""
    queryset = FacturaProveedor.objects.select_related(
        'orden__proveedor'
    ).prefetch_related('pagos').all()
    serializer_class = FacturaProveedorSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='crear')
    def crear_factura(self, request):
        serializer = FacturaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        orden_id = request.data.get('orden_id')
        try:
            orden = OrdenDeCompra.objects.get(id=orden_id)
        except OrdenDeCompra.DoesNotExist:
            return Response(
                {"error": "Orden de compra no encontrada."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if orden.estado not in ['RECIBIDA', 'PARCIAL']:
            return Response(
                {"error": "Solo se puede crear factura para órdenes recibidas."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(orden, 'factura_proveedor'):
            return Response(
                {"error": "Esta orden ya tiene una factura registrada."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        monto_calculado = sum(
            d.cantidad_recibida * d.costo_unitario
            for d in orden.detalles.all()
        )
        factura = FacturaProveedor.objects.create(
            orden=orden,
            numero_factura=datos.get('numero_factura') or f"FAC-{orden.numero_orden}",
            fecha_emision=datos['fecha_emision'],
            fecha_vencimiento=datos.get('fecha_vencimiento'),
            monto_total=monto_calculado
        )
        return Response(
            FacturaProveedorSerializer(factura).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='registrar-pago')
    def registrar_pago(self, request, pk=None):
        factura = self.get_object()

        if factura.estado == 'PAGADA':
            return Response(
                {"error": "Esta factura ya está completamente pagada."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PagoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        monto = Decimal(str(datos['monto']))

        if monto > factura.monto_pendiente:
            return Response(
                {"error": f"El monto excede el saldo pendiente (${factura.monto_pendiente:,.0f})."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            pago = PagoProveedor.objects.create(
                factura=factura,
                registrado_por=request.user,
                monto=monto,
                metodo_pago=datos['metodo_pago'],
                numero_comprobante=datos['numero_comprobante'],
                notas=datos.get('notas', '')
            )

            factura.monto_pagado += monto
            if factura.monto_pagado >= factura.monto_total:
                factura.estado = 'PAGADA'
            else:
                factura.estado = 'PARCIAL'
            factura.save()

        return Response(
            FacturaProveedorSerializer(factura).data,
            status=status.HTTP_201_CREATED
        )