from django.db import models
from django.contrib.auth.models import User

class Proveedor(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    contacto_nombre = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    def __str__(self):
        return self.nombre

# inventario/models.py
class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    codigo_barras = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    stock_minimo = models.PositiveIntegerField(default=10, verbose_name="Punto de Reorden") # Punto de reorden 
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.PROTECT, null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT) # Cada producto tiene un proveedor

    def __str__(self):
        return self.nombre

