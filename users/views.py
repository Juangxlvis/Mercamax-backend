# users/views.py
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import pyotp
from rest_framework import generics, status
from rest_framework.response import Response

from .permissions import IsAdminUser, IsTempTokenAuthenticated
from .serializers import InviteUserSerializer, LoginSerializer, RolSerializer, CustomPasswordResetSerializer
from core.models import TrustedDevice, PerfilUsuario

from rest_framework.permissions import AllowAny 
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated


class InviteUserView(generics.CreateAPIView):
    """
    Vista para que un administrador invite a un nuevo usuario al sistema.
    """
    permission_classes = [IsAdminUser]
    serializer_class = InviteUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1. Crear el usuario como inactivo y sin contraseña usable
        try:
            user = User.objects.create(
                username=data['email'],
                email=data['email'],
                first_name=data['first_name'],
                is_active=False
            )
            user.set_unusable_password()
            user.save()

            # 2. Asignar el perfil y el rol
            perfil = PerfilUsuario.objects.get(user=user)
            perfil.rol = data['rol']
            perfil.save()

            # 3. Generar token y link de activación
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_link = f"http://localhost:4200/activar-cuenta/{uid}/{token}" # URL del frontend

            # 4. Enviar el correo
            send_mail(
                '¡Bienvenido a MercaMax! Activa tu cuenta',
                f'Hola {user.first_name},\n\nPor favor, haz clic en el siguiente enlace para activar tu cuenta y establecer tu contraseña:\n\n{activation_link}\n\nGracias,\nEl equipo de MercaMax.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            return Response({'detail': 'Invitación enviada exitosamente.'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            # En caso de un error inesperado, borrar el usuario si se alcanzó a crear
            if 'user' in locals() and user.pk:
                user.delete()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            print(f"Sending 2FA email to: {user.email}")  # Debug log

            try:
                # Verificar si el usuario mandó un device_token
                device_token = request.data.get("device_token")
                if device_token:
                    try:
                        device = TrustedDevice.objects.get(user=user, device_token=device_token)
                        if device.is_valid():
                            token, _ = Token.objects.get_or_create(user=user)
                            return Response({
                                "token": token.key,
                                "username": user.username,
                                "rol": user.perfilusuario.rol,
                                "trusted": True
                            })
                    except TrustedDevice.DoesNotExist:
                        pass

                # Si no tiene dispositivo confiable → pedimos 2FA
                secret = getattr(user.perfilusuario, "otp_secret", None)
                if not secret:
                    secret = pyotp.random_base32()
                    user.perfilusuario.otp_secret = secret
                    user.perfilusuario.save()

                totp = pyotp.TOTP(secret, interval=300)  # 5 min
                code = totp.now()

                send_mail(
                    subject="Tu código de verificación MercaMax",
                    message=f"Hola {user.first_name},\n\nTu código de verificación es: {code}\n\nExpira en 5 minutos.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
                print(f"Email sent successfully to {user.email}")

                temp_token, _ = Token.objects.get_or_create(user=user)

                return Response({"step": "2fa_required", "token": temp_token.key})

            except Exception as e:
                print(f"Failed to send email: {str(e)}")
                return Response({"error": f"Failed to send 2FA email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=400)


class RolListView(APIView):
    def get(self, request):
        # Convertir PerfilUsuario.ROLES a formato esperado por el frontend
        roles = [{'value': value, 'view_value': view_value} for value, view_value in PerfilUsuario.ROLES]
        serializer = RolSerializer(roles, many=True)
        return Response(serializer.data)


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Activa una cuenta usando el UID y el token, y establece la contraseña.
        """
        try:
            uidb64 = request.data.get('uid')
            token = request.data.get('token')
            password1 = request.data.get('password1')
            password2 = request.data.get('password2')
            username = request.data.get('username')

            if not all([uidb64, token, password1, password2, username]):
                return Response({"error": "Todos los campos son requeridos."}, status=status.HTTP_400_BAD_REQUEST)
            
            if password1 != password2:
                return Response({"error": "Las contraseñas no coinciden."}, status=status.HTTP_400_BAD_REQUEST)

            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            if not user.is_active and default_token_generator.check_token(user, token):
                user.set_password(password1)
                user.is_active = True
                user.username = username
                user.save()
                return Response({"detail": "Cuenta activada exitosamente."}, status=status.HTTP_200_OK)
            
            return Response({"error": "El enlace de activación es inválido o ha caducado."}, status=status.HTTP_400_BAD_REQUEST)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            return Response({"error": "El enlace de activación es inválido o ha caducado."}, status=status.HTTP_400_BAD_REQUEST)

class ValidateTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                return Response({
                    "email": user.email,
                    "username": user.username,
                }, status=status.HTTP_200_OK)
            
            return Response({"error": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """
    Solicitar reset de contraseña: envía correo con enlace
    """
    def post(self, request):
        serializer = CustomPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"http://localhost:4200/reset-password-confirm/{uid}/{token}"  # link del frontend

        # Enviar correo
        send_mail(
            'Restablece tu contraseña en MercaMax',
            f'Hola {user.first_name},\n\nHaz clic en el siguiente enlace para restablecer tu contraseña:\n{reset_link}\n\nSi no solicitaste este cambio, ignora este correo.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        from core.models import PasswordResetRequest
        PasswordResetRequest.objects.create (user = user, email_sent = True)

        return Response({"detail": "Se ha enviado un correo para restablecer la contraseña."})


class ResetPasswordConfirmView(APIView):
    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Enlace inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Token inválido o expirado."}, status=status.HTTP_400_BAD_REQUEST)

        new_password1 = request.data.get("new_password1")
        new_password2 = request.data.get("new_password2")

        if not new_password1 or new_password1 != new_password2:
            return Response({"error": "Las contraseñas no coinciden."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password1)
        user.save()

        return Response({"message": "Contraseña restablecida exitosamente."}, status=status.HTTP_200_OK)

class Verify2FAView(APIView):
    """
    Verifica el código 2FA y otorga el token de sesión.
    """
    permission_classes = [IsTempTokenAuthenticated] 

    def post(self, request):
        code = request.data.get("code")
        remember_device = request.data.get("rememberDevice", False)
        user = request.user

        secret = getattr(user.perfilusuario, "otp_secret", None)
        if not secret:
            return Response({"error": "El usuario no tiene 2FA configurado."}, status=400)

        totp = pyotp.TOTP(secret, interval=300)
        if totp.verify(code):

            # Código correcto → creamos token final de sesión
            final_token, _ = Token.objects.get_or_create(user=user)

            response_data = {
                "token": final_token.key,
                "username": user.username,
                "rol": user.perfilusuario.rol,
                "trusted": False
            }

            #si pidió recordar dispositivo, guardamos el TrustedDevice
            if remember_device:
                device_token = secrets.token_urlsafe(32)
                expires_at = timezone.now() + timedelta(days=30)  # configurable
                TrustedDevice.objects.create(
                    user=user,
                    device_token=device_token,
                    expires_at=expires_at
                )
                response_data["trusted"] = True
                response_data["device_token"] = device_token

            return Response(response_data, status=200)

        return Response({"error": "Código inválido o expirado."}, status=400)
            