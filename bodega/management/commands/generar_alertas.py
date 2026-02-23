# bodega/management/commands/generar_alertas.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import Coalesce
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
            stock_total=Coalesce(Sum('lotes__stock_items__cantidad'), 0)
        ).filter(stock_total__lte=F('stock_minimo'))

        conteo_stock = 0
        for producto in productos_en_alerta:
            minimo = producto.stock_minimo if producto.stock_minimo is not None else 0
            mensaje = f"¡Stock bajo! Quedan {producto.stock_total or 0} de un mínimo de {minimo} para '{producto.nombre}'."
            
            for usuario in usuarios_destino:
                # Crear notificación solo si no existe una igual y no leída
                if not Notificacion.objects.filter(usuario_destino=usuario, mensaje=mensaje, leida=False).exists():
                    Notificacion.objects.create(
                        usuario_destino=usuario,
                        tipo=Notificacion.Tipo.STOCK_BAJO,
                        mensaje=mensaje
                    )
            conteo_stock += 1

        hoy = timezone.now().date()
        # --- 2. Lógica para Alertas de Lotes por Vencer ---
        fecha_limite = hoy + timedelta(days=30)
        lotes_por_vencer = Lote.objects.annotate(
            stock_total_lote=Coalesce(Sum('stock_items__cantidad'),0)
        ).filter(fecha_caducidad__gte=hoy,fecha_caducidad__lte=fecha_limite, stock_total_lote__gt=0)

        conteo_lotes = 0
        for lote in lotes_por_vencer:
            dias = (lote.fecha_caducidad - hoy).days

            if dias == 0:
                tiempo_msg = "vence HOY"
            elif dias == 1:
                tiempo_msg = "vence MAÑANA"
            else:
                tiempo_msg = f"vence en {dias} días"

            mensaje = f"¡Lote por vencer! El lote '{lote.codigo_lote}' de '{lote.producto.nombre}' {tiempo_msg}."

            for usuario in usuarios_destino:
                if not Notificacion.objects.filter(usuario_destino=usuario, mensaje=mensaje, leida=False).exists():
                    Notificacion.objects.create(
                        usuario_destino=usuario,
                        tipo=Notificacion.Tipo.LOTE_VENCE,
                        mensaje=mensaje
                    )
            conteo_lotes += 1

        self.stdout.write(self.style.SUCCESS(f'Alertas generadas: {conteo_stock} de stock, {conteo_lotes} de vencimiento.'))