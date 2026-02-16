from django.contrib import admin
from .models import CategoriaUbicacion, Ubicacion, Lote, StockItem

admin.site.register(CategoriaUbicacion)
admin.site.register(Ubicacion)
admin.site.register(Lote)
admin.site.register(StockItem)