# core/views.py
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F

from .models import Notificacion
from .serializers import NotificacionSerializer


class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        self._generar_notificaciones_stock()
        self._generar_notificaciones_vencimiento()
        return Notificacion.objects.filter(
            usuario_destino=self.request.user
        ).order_by('-fecha_creacion')

    def _generar_notificaciones_stock(self):
        from inventario.models import Producto

        productos = Producto.objects.annotate(
            stock_calculado=Sum('lotes__stock_items__cantidad')
        ).filter(stock_calculado__lte=F('stock_minimo'))

        for producto in productos:
            ya_existe = Notificacion.objects.filter(
                usuario_destino=self.request.user,
                tipo='STOCK',
                mensaje__contains=producto.nombre,
                leida=False
            ).exists()
            if not ya_existe:
                Notificacion.objects.create(
                    usuario_destino=self.request.user,
                    tipo='STOCK',
                    mensaje=f"¡Stock bajo! '{producto.nombre}' tiene {producto.stock_calculado} unidades (mínimo: {producto.stock_minimo})."
                )

    def _generar_notificaciones_vencimiento(self):
        from bodega.models import Lote

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