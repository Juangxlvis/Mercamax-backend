from django.contrib import admin
from .models import Cliente, Venta, DetalleVenta, Factura

# Registramos el Cliente
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_documento', 'numero_documento', 'email')
    search_fields = ('nombre', 'numero_documento')

# Registramos la Venta
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cajero', 'cliente', 'fecha_hora', 'estado', 'total')
    list_filter = ('estado', 'fecha_hora')
    readonly_fields = ('total',) # El total no se debe editar a mano

# Registramos el Detalle de la Venta
@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'stock_item', 'cantidad', 'precio_unitario', 'subtotal')
    readonly_fields = ('precio_unitario', 'subtotal')

# Registramos la Factura
@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'venta', 'fecha_emision')
    search_fields = ('numero_factura',)