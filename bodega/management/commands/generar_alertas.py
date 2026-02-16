# bodega/management/commands/generar_alertas.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta

from inventario.models import Producto
from bodega.models import Lote
from core.models import Notificacion

class Command(BaseCommand):
    help = 'Genera notificaciones de stock bajo y lotes por vencer para los usuarios relevantes.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando la generación de alertas...")

        # Obtener usuarios que deben recibir alertas (ej: Gerentes y Encargados de Inventario)
        usuarios_destino = User.objects.filter(perfilusuario__rol__in=['ENCARGADO_INVENTARIO', 'GERENTE_SUPERMERCADO'])

        if not usuarios_destino.exists():
            self.stdout.write(self.style.WARNING('No se encontraron usuarios destino para las alertas.'))
            return

        # --- 1. Lógica para Alertas de Stock Bajo ---
        productos_en_alerta = Producto.objects.annotate(
            stock_total=Sum('lotes__stock_items__cantidad')
        ).filter(stock_total__lte=F('stock_minimo'))

        for producto in productos_en_alerta:
            mensaje = f"¡Stock bajo! Quedan {producto.stock_total or 0} de un mínimo de {producto.stock_minimo} para '{producto.nombre}'."
            for usuario in usuarios_destino:
                # Crear notificación solo si no existe una igual y no leída
                if not Notificacion.objects.filter(usuario_destino=usuario, mensaje=mensaje, leida=False).exists():
                    Notificacion.objects.create(
                        usuario_destino=usuario,
                        tipo=Notificacion.Tipo.STOCK_BAJO,
                        mensaje=mensaje
                    )

        # --- 2. Lógica para Alertas de Lotes por Vencer ---
        fecha_limite = timezone.now().date() + timedelta(days=30)
        lotes_por_vencer = Lote.objects.annotate(
            stock_total_lote=Sum('stock_items__cantidad')
        ).filter(fecha_caducidad__lte=fecha_limite, stock_total_lote__gt=0)

        for lote in lotes_por_vencer:
            dias = (lote.fecha_caducidad - timezone.now().date()).days
            mensaje = f"¡Lote por vencer! El lote '{lote.codigo_lote}' de '{lote.producto.nombre}' vence en {dias} días."
            for usuario in usuarios_destino:
                if not Notificacion.objects.filter(usuario_destino=usuario, mensaje=mensaje, leida=False).exists():
                    Notificacion.objects.create(
                        usuario_destino=usuario,
                        tipo=Notificacion.Tipo.LOTE_VENCE,
                        mensaje=mensaje
                    )

        self.stdout.write(self.style.SUCCESS('Generación de alertas completada.'))