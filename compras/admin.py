# compras/admin.py
from django.contrib import admin
from .models import OrdenDeCompra, DetalleOrdenDeCompra

admin.site.register(OrdenDeCompra)
admin.site.register(DetalleOrdenDeCompra)