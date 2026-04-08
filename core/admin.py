# core/admin.py
from django.contrib import admin
from .models import PerfilUsuario, Notificacion
from django.contrib.sessions.models import Session

admin.site.register(PerfilUsuario)
admin.site.register(Notificacion)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()
    list_display = ['session_key', '_session_data', 'expire_date']