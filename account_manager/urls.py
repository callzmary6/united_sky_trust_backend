from django.urls import path

from .views import GetRegisteredUsers, FundAccount, GetTransactions, UpdateAccountProfile, GetVirtualCards, ActivateVirtualCard, GetUserDetail, AccountUserTransactions, DeleteTransaction,UpdateTransactionView, GetChequeDeposits, ApproveChequeDeposit, GetKYC

urlpatterns = [
    path('get_registered_users', GetRegisteredUsers.as_view(), name='get-registered-users'),
    path('get_user/<str:id>', GetUserDetail.as_view(), name='get-user-detail'),
    path('fund_account/<str:acn>', FundAccount.as_view(), name='find-account'),
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
]
