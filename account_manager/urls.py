from django.urls import path

from .views import GetRegisteredUsers, FundAccount, GetTransactions, UpdateAccountProfile, GetVirtualCards, ActivateVirtualCard, GetUserDetail, AccountUserTransactions, DeleteTransaction,UpdateTransactionView, GetChequeDeposits, ApproveChequeDeposit, GetKYC, DeleteChequeDeposit, DeleteKYC, ApproveKYC, WireTransfer, GetTotalRegisteredUsers, GetTotalTransactions, GetTotalUnverifiedUsers, GetTotalChequeDeposits, GetChartData, GetCurrencyChartData, SendCustomEmail, CreateCommentView, GetComments, GetSupportTicket

urlpatterns = [
    path('get_registered_users', GetRegisteredUsers.as_view(), name='get-registered-users'),
    path('get_user/<str:id>', GetUserDetail.as_view(), name='get-user-detail'),
    path('fund_account/<str:user_id>', FundAccount.as_view(), name='find-account'),
    path('get_transactions', GetTransactions.as_view(), name='get-transactions'),
    path('user_transaction_details/<str:id>', AccountUserTransactions.as_view(), name='account-transaction-details'),
    path('delete_transaction/<str:id>', DeleteTransaction.as_view(), name='delete-transaction'),
    path('update_transaction/<str:id>', UpdateTransactionView.as_view(), name='update_transaction'),

    path('update_profile', UpdateAccountProfile.as_view(), name='update-account'),
    path('get_virtual_cards', GetVirtualCards.as_view(), name='get-virtual-cards'),
    path('activate_virtual_card/<str:vc_id>', ActivateVirtualCard.as_view(), name='activate-virtual-card'),
    path('get_cheque_deposits', GetChequeDeposits.as_view(), name='get-check-deposit'),
    path('get_kycs', GetKYC.as_view(), name='get-kycs'),
    path('approve_cheque_deposit/<str:cheque_id>', ApproveChequeDeposit.as_view(), name='approve-cheque-deposit'),
    path('delete_cheque_deposit/<str:cheque_id>', DeleteChequeDeposit.as_view(), name='delete-cheque-deposit'),
    path('delete_kyc/<str:kyc_id>', DeleteKYC.as_view(), name='delete-kyc'),
    path('approve_kyc/<str:kyc_id>', ApproveKYC.as_view(), name='approve-kyc'),
    path('wire_transfer', WireTransfer.as_view(), name='wire-transfer'),

    # Dashboard endpoints
    path('total_users', GetTotalRegisteredUsers.as_view(), name='total-users'),
    path('total_unverified_users', GetTotalUnverifiedUsers.as_view(), name='get-unverified-users'),
    path('total_cheque_deposits', GetTotalChequeDeposits.as_view(), name='total-cheque-deposits'),
    path('total_transactions', GetTotalTransactions.as_view(), name='total-transactions'),
    path('get_chart_data', GetChartData.as_view(), name='get-chart-data'),
    path('get_currency_users', GetCurrencyChartData.as_view(), name='get-currency-users'),
    path('send_custom_email', SendCustomEmail.as_view(), name='send-custom-email'),

    # Support Ticket endpoints
    path('create_comment/<str:support_ticket_id>', CreateCommentView.as_view(), name='create-comment'),
    path('get_comments/<str:support_ticket_id>', GetComments.as_view(), name='get-comments'),
    path('get_support_tickets', GetSupportTicket.as_view(), name='get-support-tickets'),
]
