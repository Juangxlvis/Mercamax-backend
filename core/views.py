from django.shortcuts import render

# core/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Notificacion
from .serializers import NotificacionSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Notificacion
from django.contrib.auth import get_user_model

def generar_notificaciones_stock():
    """Crea notificaciones de stock bajo para todos los gerentes/encargados."""
    from inventario.models import Producto
    from django.db.models import Sum

    User = get_user_model()
    # Destinatarios: encargados y gerentes
    destinatarios = User.objects.filter(
        perfilusuario__rol__in=['ENCARGADO_INVENTARIO', 'GERENTE_SUPERMERCADO']
    )

    productos_con_stock = Producto.objects.annotate(
        stock_calculado=Sum('lotes__stock_items__cantidad')
    ).filter(stock_calculado__lte=models.F('stock_minimo'))

    for producto in productos_con_stock:
        for usuario in destinatarios:
            # Evitar duplicados — no crear si ya existe una no leída igual
            ya_existe = Notificacion.objects.filter(
                usuario_destino=usuario,
                tipo='STOCK',
                mensaje__contains=producto.nombre,
                leida=False
            ).exists()

            if not ya_existe:
                Notificacion.objects.create(
                    usuario_destino=usuario,
                    tipo='STOCK',
                    mensaje=f"¡Stock bajo! '{producto.nombre}' tiene {producto.stock_calculado} unidades (mínimo: {producto.stock_minimo})."
                )


def generar_notificaciones_vencimiento():
    """Crea notificaciones de lotes próximos a vencer."""
    from bodega.models import Lote
    from django.db.models import Sum

    User = get_user_model()
    destinatarios = User.objects.filter(
        perfilusuario__rol__in=['ENCARGADO_INVENTARIO', 'GERENTE_SUPERMERCADO']
    )

    fecha_limite = timezone.now().date() + timedelta(days=30)
    lotes_por_vencer = Lote.objects.annotate(
        stock_total_lote=Sum('stock_items__cantidad')
    ).filter(
        fecha_caducidad__lte=fecha_limite,
        stock_total_lote__gt=0
    )

    for lote in lotes_por_vencer:
        dias = (lote.fecha_caducidad - timezone.now().date()).days
        for usuario in destinatarios:
            ya_existe = Notificacion.objects.filter(
                usuario_destino=usuario,
                tipo='VENCE',
                mensaje__contains=lote.codigo_lote,
                leida=False
            ).exists()

            if not ya_existe:
                Notificacion.objects.create(
                    usuario_destino=usuario,
                    tipo='VENCE',
                    mensaje=f"Lote '{lote.codigo_lote}' de '{lote.producto.nombre}' vence en {dias} días."
                )

class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ✅ Genera notificaciones automáticamente cada vez que se consultan
        self._generar_notificaciones_stock()
        self._generar_notificaciones_vencimiento()
        return Notificacion.objects.filter(
            usuario_destino=self.request.user
        ).order_by('-fecha_creacion')

    def _generar_notificaciones_stock(self):
        from inventario.models import Producto
        from django.db.models import Sum, F
        from django.db import models

        destinatarios = [self.request.user]
        productos = Producto.objects.annotate(
            stock_calculado=Sum('lotes__stock_items__cantidad')
        ).filter(stock_calculado__lte=F('stock_minimo'))

        for producto in productos:
            for usuario in destinatarios:
                ya_existe = Notificacion.objects.filter(
                    usuario_destino=usuario,
                    tipo='STOCK',
                    mensaje__contains=producto.nombre,
                    leida=False
                ).exists()
                if not ya_existe:
                    Notificacion.objects.create(
                        usuario_destino=usuario,
                        tipo='STOCK',
                        mensaje=f"¡Stock bajo! '{producto.nombre}' tiene {producto.stock_calculado} unidades (mínimo: {producto.stock_minimo})."
                    )

    def _generar_notificaciones_vencimiento(self):
        from bodega.models import Lote
        from django.db.models import Sum
        from django.utils import timezone
        from datetime import timedelta

        fecha_limite = timezone.now().date() + timedelta(days=30)
        lotes = Lote.objects.annotate(
            stock_total_lote=Sum('stock_items__cantidad')
        ).filter(
            fecha_caducidad__lte=fecha_limite,
            stock_total_lote__gt=0
        )

        for lote in lotes:
            dias = (lote.fecha_caducidad - timezone.now().date()).days
            ya_existe = Notificacion.objects.filter(
                usuario_destino=self.request.user,
                tipo='VENCE',
                mensaje__contains=lote.codigo_lote,
                leida=False
            ).exists()
            if not ya_existe:
                Notificacion.objects.create(
                    usuario_destino=self.request.user,
                    tipo='VENCE',
                    mensaje=f"Lote '{lote.codigo_lote}' de '{lote.producto.nombre}' vence en {dias} días."
                )
    
class MarcarTodasLeidasView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacion.objects.filter(
            usuario_destino=request.user,
            leida=False
        ).update(leida=True)
        return Response({'detail': 'Todas las notificaciones marcadas como leídas.'})