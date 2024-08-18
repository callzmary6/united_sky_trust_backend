from django.urls import path
from .views import GetTransactions, VerifyCOTCode, VerifyIMFCode, OTPVerifyView, TransferFundsView,   CheckAccountBalance, GetUserTransactions, VirtualCardRequest, FundVirtualCard, GetVirtualCards,GetPercentageExpenses, SupportTicketView, CheckDepositRequest

urlpatterns = [
    path('get_transactions', GetTransactions.as_view(), name='transactions'),
    path('percentage_expense', GetPercentageExpenses.as_view(), name='percentage-expense'),
    path('verify_imf', VerifyIMFCode.as_view(), name='verify-imf'),
    path('verify_cot', VerifyCOTCode.as_view(), name='verify-cot'),
    path('verify_otp', OTPVerifyView.as_view(), name='verify-otp'),
    path('check_acct_bal', CheckAccountBalance.as_view(), name='check-account-balance'),
    path('transfer_funds', TransferFundsView.as_view(), name='transfer-funds'),
    path('user_transactions', GetUserTransactions.as_view(), name='get-user-transactions'),
    path('request_virtual_card', VirtualCardRequest.as_view(), name='request-virtual-card'),
    path('fund_virtual_card/<str:vc_id>', FundVirtualCard.as_view(), name='fund-virtual-card'),
    path('virtual_cards', GetVirtualCards.as_view(), name='get-virtual-cards'), 

    path('create_support_ticket', SupportTicketView.as_view(), name='create-support-ticket'),
    path('request_check_deposit', CheckDepositRequest.as_view(), name='request-check-deposit'),

]
