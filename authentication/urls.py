from django.urls import path

from .views import RegisterAccountManager, LoginAccountManager, CreateAccountUser, PasswordResetView, SuspendAccountUser

urlpatterns = [
    path('register', RegisterAccountManager.as_view(), name='register'),
    path('login', LoginAccountManager.as_view(), name='login'),
    path('register_user',  CreateAccountUser.as_view(), name='register-user'),
    path('reset_password', PasswordResetView.as_view(), name='password-reset'),
    path('suspend_user/<str:acc_id>', SuspendAccountUser.as_view(), name='suspend-user'),
]
