# compras/models.py
from django.db import models
from django.conf import settings


class OrdenDeCompra(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('RECIBIDA', 'Recibida'),
        ('PARCIAL', 'Recepción Parcial'),
        ('CANCELADA', 'Cancelada'),
    ]

    proveedor = models.ForeignKey(
        'inventario.Proveedor',
        on_delete=models.PROTECT,
        related_name='ordenes_compra'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ordenes_creadas',
        null=True
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes_aprobadas'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_estimada_entrega = models.DateField(
        null=True, blank=True,
        help_text="Debe ser igual o posterior a la fecha actual"
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )
    motivo_rechazo = models.TextField(
        blank=True, null=True,
        help_text="Obligatorio si el estado es RECHAZADA"
    )
    notas = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"

    def __str__(self):
        return f"OC-{self.id:06d} - {self.proveedor.nombre} [{self.estado}]"

    @property
    def numero_orden(self):
        return f"OC-{self.id:06d}"

    @property
    def total(self):
        return sum(
            d.cantidad_solicitada * d.costo_unitario
            for d in self.detalles.all()
        )


class DetalleOrdenDeCompra(models.Model):
    orden = models.ForeignKey(
        OrdenDeCompra,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'inventario.Producto',
        on_delete=models.PROTECT,
        related_name='detalles_compra'
    )
    cantidad_solicitada = models.PositiveIntegerField()
    cantidad_recibida = models.PositiveIntegerField(
        default=0,
        help_text="Se actualiza al registrar recepción"
    )
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad_solicitada}x {self.producto.nombre} (OC-{self.orden.id:06d})"

    @property
    def subtotal(self):
        return self.cantidad_solicitada * self.costo_unitario


class RecepcionMercancia(models.Model):
    """RF-P03: Registro de recepción de mercancía vinculada a una orden aprobada."""
    orden = models.ForeignKey(
        OrdenDeCompra,
        on_delete=models.PROTECT,
        related_name='recepciones'
    )
    recibido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recepciones_registradas'
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    factura_proveedor = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="Número de factura del proveedor"
    )
    notas = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_recepcion']
        verbose_name = "Recepción de Mercancía"

    def __str__(self):
        return f"Recepción #{self.id} - {self.orden.numero_orden}"


class DetalleRecepcion(models.Model):
    """Detalle de cada producto recibido en una recepción."""
    ESTADO_CHOICES = [
        ('CONFORME', 'Conforme'),
        ('NO_CONFORME', 'No Conforme'),
    ]

    recepcion = models.ForeignKey(
        RecepcionMercancia,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    detalle_orden = models.ForeignKey(
        DetalleOrdenDeCompra,
        on_delete=models.PROTECT,
        related_name='recepciones'
    )
    cantidad_recibida = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='CONFORME'
    )
    observacion = models.TextField(
        blank=True, null=True,
        help_text="Obligatorio si el estado es NO_CONFORME"
    )
    fecha_caducidad = models.DateField(
        null=True, blank=True,
        help_text="Fecha de caducidad del lote recibido"
    )

    def __str__(self):
        return f"{self.cantidad_recibida}x {self.detalle_orden.producto.nombre} [{self.estado}]"


class FacturaProveedor(models.Model):
    """RF-P05: Factura vinculada a una orden recibida para gestionar pagos."""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Pago Parcial'),
        ('PAGADA', 'Pagada'),
    ]

    orden = models.OneToOneField(
        OrdenDeCompra,
        on_delete=models.PROTECT,
        related_name='factura_proveedor'
    )
    numero_factura = models.CharField(max_length=100, unique=True)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = "Factura de Proveedor"

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.orden.proveedor.nombre}"

    @property
    def monto_pendiente(self):
        return self.monto_total - self.monto_pagado


class PagoProveedor(models.Model):
    """RF-P05: Registro de pagos realizados a proveedores."""
    METODO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('CHEQUE', 'Cheque'),
    ]

    factura = models.ForeignKey(
        FacturaProveedor,
        on_delete=models.PROTECT,
        related_name='pagos'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pagos_registrados'
    )
    fecha_pago = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES)
    numero_comprobante = models.CharField(
        max_length=100,
        help_text="Número de comprobante o referencia del pago"
    )
    notas = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_pago']
        verbose_name = "Pago a Proveedor"

    def __str__(self):
        return f"Pago ${self.monto} - {self.factura.numero_factura}"