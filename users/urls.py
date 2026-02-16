from django.urls import path
from .views import InviteUserView, RolListView, ActivateAccountView, ValidateTokenView, ForgotPasswordView, ResetPasswordConfirmView

urlpatterns = [
    path('admin/invite/', InviteUserView.as_view(), name='invite-user'),
    path('api/roles/', RolListView.as_view(), name='roles-list'),
    path('complete-registration/', ActivateAccountView.as_view(), name='complete-registration'),
    path('password/reset/', ForgotPasswordView.as_view(), name='password_reset'),
    path('password/reset/confirm/<uidb64>/<token>/', ResetPasswordConfirmView.as_view(), name='password_reset_confirm'),    
]