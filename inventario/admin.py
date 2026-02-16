# inventario/admin.py
from django.contrib import admin
from .models import Proveedor, Producto, CategoriaProducto

admin.site.register(Proveedor)
admin.site.register(Producto)
admin.site.register(CategoriaProducto)