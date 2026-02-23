from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, F

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
    
    @property
    def stock_total(self):
        # Importamos aquí adentro para evitar que Django se confunda (importación circular)
        from bodega.models import StockItem 
        
        total = StockItem.objects.filter(lote__producto=self).aggregate(total=Sum('cantidad'))['total']
        return total or 0

    # --- SUPERPODER 2: Calcular Costo Promedio Ponderado ---
    @property
    def costo_promedio_ponderado(self):
        from bodega.models import StockItem
        
        # Multiplicamos la cantidad de cajas por lo que costó ese lote en específico
        resultado = StockItem.objects.filter(lote__producto=self).aggregate(
            valor_total=Sum(F('cantidad') * F('lote__costo_compra_lote')),
            cantidad_total=Sum('cantidad')
        )
        
        valor_total = resultado['valor_total'] or 0
        cantidad_total = resultado['cantidad_total'] or 0
        
        if cantidad_total > 0:
            return valor_total / cantidad_total
        return 0

