from rest_framework import permissions
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

class IsAdminUser(permissions.BasePermission):
    """
    Permiso personalizado para permitir solo a administradores (Gerente o superuser).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Permite el acceso si es un superusuario o si tiene el rol de Gerente.
        return request.user.is_superuser or (
            hasattr(request.user, 'perfilusuario') and 
            request.user.perfilusuario.rol == 'GERENTE_SUPERMERCADO'
        )

class IsTempTokenAuthenticated(permissions.BasePermission):
    """
    Permiso que valida un token temporal para 2FA.
    """
    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return False

        try:
            prefix, key = auth_header.split()
            if prefix.lower() != 'token':
                return False

            token = Token.objects.get(key=key)
            request.user = token.user  # asignamos el usuario al request
            return True

        except (ValueError, Token.DoesNotExist):
            raise AuthenticationFailed('Token temporal inválido.')