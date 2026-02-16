from rest_framework import serializers
from django.contrib.auth.models import User
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetSerializer
from django.contrib.auth import authenticate
from core.models import PerfilUsuario

class InviteUserSerializer(serializers.Serializer):
    """
    Serializer para validar los datos de la invitación de un nuevo usuario.
    """
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    rol = serializers.ChoiceField(choices=PerfilUsuario.ROLES)

class RolSerializer(serializers.Serializer):
    value = serializers.CharField()
    view_value = serializers.CharField()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    rol = serializers.ChoiceField(choices=PerfilUsuario.ROLES)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")
        rol = data.get("rol")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Usuario o contraseña incorrectos.")

        try:
            perfil = PerfilUsuario.objects.get(user=user)
        except PerfilUsuario.DoesNotExist:
            raise serializers.ValidationError("El usuario no tiene un perfil asociado.")

        if perfil.rol != rol:
            raise serializers.ValidationError("El rol seleccionado no corresponde con este usuario.")
        
        data["user"] = user
        return data
    
class CustomRegisterSerializer( RegisterSerializer):
    # eliminamos el email, solo pedimos username y password
    username = serializers.CharField(required=True)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    # sobreescribimos para no pedir email
    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        return {
            'username': data.get('username', ''),
            'password1': data.get('password1', ''),
            'password2': data.get('password2', ''),
        }

class CustomPasswordResetSerializer(PasswordResetSerializer):
    """Personaliza el serializer de reset de contraseña"""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Opcional: validar que el email exista en la base de datos"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No existe ningún usuario con este correo.")
        return value

class CustomSetPasswordSerializer(serializers.Serializer):
    new_password1  = serializers.CharField(write_only = True)
    new_password2  = serializers.CharField(write_only = True)

    def validate(self, data):
        if data ['new_password1'] != data['new_password2']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
            return data

class ActivateAccountSerializer(serializers.Serializer):
    """
    Serializer para validar los datos de activación de cuenta.
    """
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})