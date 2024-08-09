from django.urls import path

from .views import GetRegisteredUsers, FundAccount, GetTransactions, UpdateAccountProfile, GetVirtualCards, ActivateVirtualCard

urlpatterns = [
    path('get_registered_users', GetRegisteredUsers.as_view(), name='get-registered-users'),
    path('fund_account/<str:acn>', FundAccount.as_view(), name='find-account'),
    path('get_transactions', GetTransactions.as_view(), name='get-transactions'),

    path('update_profile', UpdateAccountProfile.as_view(), name='update-account'),
    path('get_virtual_cards', GetVirtualCards.as_view(), name='get-virtual-cards'),
    path('activate_virtual_card/<str:vc_id>', ActivateVirtualCard.as_view(), name='activate-virtual-card'),
]
