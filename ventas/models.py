from django.db import models
from django.contrib.auth.models import User

class Venta(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    cajero = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ventas_realizadas')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Venta #{self.id} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) # Precio al momento de la venta
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
