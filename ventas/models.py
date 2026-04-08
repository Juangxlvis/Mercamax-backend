# ventas/models.py
from django.db import models
from django.conf import settings
from bodega.models import StockItem


class Cliente(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('NIT', 'NIT'),
        ('CE', 'Cédula de Extranjería'),
        ('PAS', 'Pasaporte'),
    ]
    nombre = models.CharField(max_length=200)
    tipo_documento = models.CharField(max_length=3, choices=TIPO_DOCUMENTO_CHOICES, default='CC')
    numero_documento = models.CharField(max_length=50, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.tipo_documento} {self.numero_documento})"


class Venta(models.Model):
    ESTADO_CHOICES = [
        ('COMPLETADA', 'Completada'),
        ('ANULADA', 'Anulada'),
    ]
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
        ('TARJETA_DEBITO', 'Tarjeta de Débito'),
        ('TRANSFERENCIA', 'Transferencia'),
    ]

    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas_realizadas'
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ventas'
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='COMPLETADA')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='EFECTIVO')

    # Desglose contable
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                   help_text="Suma de precios base sin impuestos")
    total_impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                          help_text="Suma de todos los IVAs calculados por producto")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                help_text="subtotal + total_impuestos")
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        cliente_nombre = self.cliente.nombre if self.cliente else "Anónimo"
        return f"Venta #{self.id} - {cliente_nombre} - ${self.total}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalleventa_set')
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name='ventas_asociadas')
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                          help_text="IVA capturado al momento de la venta")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_linea = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        from decimal import Decimal
        self.subtotal = self.cantidad * self.precio_unitario
        self.impuesto = self.subtotal * (self.porcentaje_iva / Decimal('100'))
        self.total_linea = self.subtotal + self.impuesto
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.stock_item.lote.producto.nombre} (Venta #{self.venta.id})"


class Factura(models.Model):
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='factura')
    numero_factura = models.CharField(max_length=20, unique=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Factura {self.numero_factura} (Venta #{self.venta.id})"