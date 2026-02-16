from django.contrib import admin
from django.urls import path, include
from users.views import LoginView, Verify2FAView, ValidateTokenView


urlpatterns = [
    path('admin/', admin.site.urls),
    #APIs de módulos
    path('api/inventario/', include('inventario.urls')),
    path('api/users/', include('users.urls')),
    path('api/bodega/', include('bodega.urls')),

    # Autenticación principal
    path('api/auth/login/', LoginView.as_view(), name='custom-login'),
    path('api/auth/verify-2fa/', Verify2FAView.as_view(), name = 'verify-2fa'),
    path('api/auth/validate-token/', ValidateTokenView.as_view(), name = 'validate-token'),

    # Rutas de autenticación
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    path('accounts/', include('allauth.urls')),
]
