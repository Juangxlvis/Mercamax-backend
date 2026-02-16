from django.db import models
from django.contrib.auth.models import User

class OrdenDeCompra(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    proveedor = models.ForeignKey('inventario.Proveedor', on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    def __str__(self):
        return f"Orden #{self.id} a {self.proveedor.nombre}"

class DetalleOrdenDeCompra(models.Model):
    orden = models.ForeignKey(OrdenDeCompra, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT)
    cantidad_solicitada = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)