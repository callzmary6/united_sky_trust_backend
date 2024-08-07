from django.urls import path
from .views import GetTransactions, VerifyCOTCode, VerifyIMFCode, OTPVerifyView, TransferFundsView,   CheckAccountBalance

urlpatterns = [
    path('get_transactions', GetTransactions.as_view(), name='transactions'),
    path('verify_imf', VerifyIMFCode.as_view(), name='verify-imf'),
    path('verify_cot', VerifyCOTCode.as_view(), name='verify-cot'),
    path('verify_otp', OTPVerifyView.as_view(), name='verify-otp'),
    path('check_acct_bal', CheckAccountBalance.as_view(), name='check-account-balance'),
    path('transfer_funds', TransferFundsView.as_view(), name='transfer-funds'),
]
