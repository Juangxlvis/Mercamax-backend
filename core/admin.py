# core/admin.py
from django.contrib import admin
from .models import PerfilUsuario, Notificacion


admin.site.register(PerfilUsuario)
admin.site.register(Notificacion)