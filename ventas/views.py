# ventas/views.py
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from .models import Cliente, Venta, DetalleVenta, Factura
from bodega.models import StockItem
from .serializers import ClienteSerializer, VentaSerializer, VentaCreateSerializer
from .pdf_generator import generar_pdf_factura


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    @action(detail=False, methods=['get'], url_path='buscar')
    def buscar(self, request):
        q = request.query_params.get('q', '')
        if not q:
            return Response([])
        clientes = self.queryset.filter(
            Q(numero_documento__icontains=q) | Q(nombre__icontains=q)
        )
        return Response(self.get_serializer(clientes, many=True).data)


class BuscarProductoVentaView(APIView):
    def get(self, request):
        q = request.query_params.get('q', '')
        if not q:
            return Response([])

        stock_items = StockItem.objects.select_related(
            'lote__producto', 'ubicacion'
        ).filter(cantidad__gt=0).filter(
            Q(lote__producto__nombre__icontains=q) |
            Q(lote__producto__codigo_barras__icontains=q)
        )

        resultados = []
        for item in stock_items:
            producto = item.lote.producto
            resultados.append({
                "stock_item_id": item.id,
                "producto_nombre": producto.nombre,
                "codigo_barras": producto.codigo_barras,
                "precio_venta": str(producto.precio_venta),
                "porcentaje_iva": str(producto.porcentaje_iva),  # ✅ IVA por producto
                "stock_disponible": item.cantidad,
                "ubicacion": item.ubicacion.nombre,
                "lote_codigo": item.lote.codigo_lote
            })
        return Response(resultados)


class VentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Venta.objects.select_related(
        'cajero', 'cliente', 'factura'
    ).prefetch_related(
        'detalleventa_set__stock_item__lote__producto'
    ).all().order_by('-fecha_hora')
    serializer_class = VentaSerializer

    @action(detail=False, methods=['post'], url_path='crear')
    def crear_venta(self, request):
        serializer = VentaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        try:
            with transaction.atomic():
                cliente_id = datos.get('cliente_id')
                cliente = Cliente.objects.get(id=cliente_id) if cliente_id else None

                venta = Venta.objects.create(
                    cajero=request.user,
                    cliente=cliente,
                    estado='COMPLETADA',
                    metodo_pago=datos.get('metodo_pago', 'EFECTIVO'),
                    subtotal=0,
                    total_impuestos=0,
                    total=0,
                    notas=datos.get('notas', '')
                )

                subtotal_total = Decimal('0.00')
                impuestos_total = Decimal('0.00')

                for item_data in datos['items']:
                    stock_item = StockItem.objects.select_for_update().get(
                        id=item_data['stock_item_id']
                    )
                    cantidad = item_data['cantidad']

                    if stock_item.cantidad < cantidad:
                        raise ValueError(
                            f"Stock insuficiente para '{stock_item.lote.producto.nombre}'. "
                            f"Disponible: {stock_item.cantidad}"
                        )

                    # Descontar stock
                    stock_item.cantidad -= cantidad
                    stock_item.save()

                    producto = stock_item.lote.producto
                    precio_unitario = producto.precio_venta
                    iva_producto = producto.porcentaje_iva

                    subtotal_linea = Decimal(str(cantidad)) * precio_unitario
                    impuesto_linea = subtotal_linea * (iva_producto / Decimal('100'))

                    subtotal_total += subtotal_linea
                    impuestos_total += impuesto_linea

                    DetalleVenta.objects.create(
                        venta=venta,
                        stock_item=stock_item,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        porcentaje_iva=iva_producto,
                        subtotal=subtotal_linea,
                        impuesto=impuesto_linea,
                        total_linea=subtotal_linea + impuesto_linea
                    )

                # Guardar totales
                venta.subtotal = subtotal_total
                venta.total_impuestos = impuestos_total
                venta.total = subtotal_total + impuestos_total
                venta.save()

                # Generar factura
                numero = f"FAC-{Factura.objects.count() + 1:06d}"
                Factura.objects.create(venta=venta, numero_factura=numero)

            # Recargar con relaciones completas
            venta_creada = Venta.objects.select_related(
                'cajero', 'cliente', 'factura'
            ).prefetch_related(
                'detalleventa_set__stock_item__lote__producto'
            ).get(id=venta.id)

            # ── Envío de factura por correo (no bloquea la venta) ──────
            try:
                cliente_obj = venta_creada.cliente
                if cliente_obj and cliente_obj.email:
                    from users.gmail_sender import send_factura_email
                    pdf_bytes = generar_pdf_factura(venta_creada)
                    total_fmt = f"${float(venta_creada.total):,.0f} COP"
                    send_factura_email(
                        to_email=cliente_obj.email,
                        nombre=cliente_obj.nombre,
                        numero_factura=venta_creada.factura.numero_factura,
                        total=total_fmt,
                        pdf_bytes=pdf_bytes
                    )
            except Exception as e:
                # Falla silenciosamente — la venta ya está guardada
                print(f"[AVISO] No se pudo enviar correo de factura: {e}")

            return Response(VentaSerializer(venta_creada).data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True, methods=['post'], url_path='anular')
    def anular_venta(self, request, pk=None):
        venta = self.get_object()
        if venta.estado == 'ANULADA':
            return Response({"error": "La venta ya está anulada."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                for detalle in venta.detalleventa_set.all():
                    detalle.stock_item.cantidad += detalle.cantidad
                    detalle.stock_item.save()
                venta.estado = 'ANULADA'
                venta.save()
            return Response({"mensaje": f"Venta #{venta.id} anulada y stock devuelto."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='pdf')
    def descargar_pdf(self, request, pk=None):
        venta = self.get_object()
        if not hasattr(venta, 'factura'):
            return Response({"error": "Sin factura generada."}, status=status.HTTP_404_NOT_FOUND)

        pdf_bytes = generar_pdf_factura(venta)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="factura_{venta.factura.numero_factura}.pdf"'
        )
        return response