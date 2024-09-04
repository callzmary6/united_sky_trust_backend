from django.urls import path
from .views import OTPVerifyView, TransferFundsView,   CheckAccountBalance, GetAccountSummary, VirtualCardRequest, FundVirtualCard, GetVirtualCards,GetExpensesTotal, CreateSupportTicketView, ChequeDepositRequest, CreateCommentView, GetUserDetails, LinkRealCard, WireTransfer, ApplyKYC, GetRealLInkedCards, GetPastDebitCredit, GetLastFiveTransactions, SendTransferOtp

urlpatterns = [
    # path('get_transactions', GetTransactions.as_view(), name='transactions'),
    path('verify_otp', OTPVerifyView.as_view(), name='verify-otp'),
    path('check_acct_bal', CheckAccountBalance.as_view(), name='check-account-balance'),
    path('transfer_funds', TransferFundsView.as_view(), name='transfer-funds'),
    path('account_summary', GetAccountSummary.as_view(), name='get-account-summary'),
    path('request_virtual_card', VirtualCardRequest.as_view(), name='request-virtual-card'),
    path('fund_virtual_card/<str:vc_id>', FundVirtualCard.as_view(), name='fund-virtual-card'),
    path('virtual_cards', GetVirtualCards.as_view(), name='get-virtual-cards'), 
    path('request_cheque_deposit', ChequeDepositRequest.as_view(), name='request-check-deposit'),
    path('get_user_details', GetUserDetails.as_view(), name='get-user-details'),
    path('user_wire_transfer', WireTransfer.as_view(), name='user-wire-transafer'),
    path('apply_kyc', ApplyKYC.as_view(), name='apply-kyc'),

    # Support Ticket Endpoints
    path('create_support_ticket', CreateSupportTicketView.as_view(), name='create-support-ticket'),
    path('create_comment/<str:support_ticket_id>', CreateCommentView.as_view(), name='create-comment'),

    path('link_card', LinkRealCard.as_view(), name='link-real-card'),
    path('get_real_cards', GetRealLInkedCards.as_view(), name='get-real-linked-cards'),
    path('get_past_expenses', GetPastDebitCredit.as_view(), name='get-past-expense'),
    path('expenses_total', GetExpensesTotal.as_view(), name='get-total-expenses'),
    path('last_five_transactions', GetLastFiveTransactions.as_view(), name='get-last-five-transactions'),
    path('send_transfer_otp', SendTransferOtp.as_view(), name='send-transfer-otp'),
]
