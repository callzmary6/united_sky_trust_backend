from django.urls import path

from .views import RegisterAccountManager, LoginAccountManager, CreateAccountUser, PasswordResetView, SuspendAccountUser, VerifyAccountUser, ApproveAccountUser, TwoFactorAuthentication, LoginAccountUser, GenerateOTPCode,  ReturnTransactions

urlpatterns = [
    path('register_admin', RegisterAccountManager.as_view(), name='register'),
    path('login_admin', LoginAccountManager.as_view(), name='login'),
    path('register_user',  CreateAccountUser.as_view(), name='register-user'),
    path('login_user', LoginAccountUser.as_view(), name='login-user'),
    path('verify_user/<str:user_id>', VerifyAccountUser.as_view(), name='verify-account'),
    path('reset_password', PasswordResetView.as_view(), name='password-reset'),
    path('suspend_user/<str:acc_id>', SuspendAccountUser.as_view(), name='suspend-user'),
    path('approve_user/<str:acc_id>', ApproveAccountUser.as_view(), name='approve-account'),
    path('2fa/<str:acc_id>', TwoFactorAuthentication.as_view(), name='enable-2fa'),
    path('regenerate_otp/<str:user_id>/<str:no_otp>', GenerateOTPCode.as_view(), name='regenerate-otp'),

    path('transactions/', ReturnTransactions.as_view(), name='transactions'),
]
