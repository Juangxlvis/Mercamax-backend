from django.shortcuts import render

# core/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Notificacion
from .serializers import NotificacionSerializer
from rest_framework.views import APIView
from rest_framework.response import Response

class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Devolver solo las notificaciones del usuario logueado, las más recientes primero
        return Notificacion.objects.filter(usuario_destino=self.request.user).order_by('-fecha_creacion')
    
class MarcarTodasLeidasView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacion.objects.filter(
            usuario_destino=request.user,
            leida=False
        ).update(leida=True)
        return Response({'detail': 'Todas las notificaciones marcadas como leídas.'})