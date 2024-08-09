from django.urls import path
from .views import GetTransactions, VerifyCOTCode, VerifyIMFCode, OTPVerifyView, TransferFundsView,   CheckAccountBalance, GetUserTransactions, VirtualCardRequest, FundVirtualCard, GetVirtualCards

urlpatterns = [
    path('get_transactions', GetTransactions.as_view(), name='transactions'),
    path('verify_imf', VerifyIMFCode.as_view(), name='verify-imf'),
    path('verify_cot', VerifyCOTCode.as_view(), name='verify-cot'),
    path('verify_otp', OTPVerifyView.as_view(), name='verify-otp'),
    path('check_acct_bal', CheckAccountBalance.as_view(), name='check-account-balance'),
    path('transfer_funds', TransferFundsView.as_view(), name='transfer-funds'),
    path('user_transactions', GetUserTransactions.as_view(), name='get-user-transactions'),
    path('request_virtual_card', VirtualCardRequest.as_view(), name='request-virtual-card'),
    path('fund_virtual_card/<str:vc_id>', FundVirtualCard.as_view(), name='fund-virtual-card'),
    path('virtual_cards', GetVirtualCards.as_view(), name='get-virtual-cards'), 
]
