from django.urls import path

from .views import GetRegisteredUsers, FundAccount, GetTransactions, UpdateAccountProfile

urlpatterns = [
    path('get_registered_users', GetRegisteredUsers.as_view(), name='get-registered-users'),
    path('fund_account/<str:acn>', FundAccount.as_view(), name='find-account'),
    path('get_transactions', GetTransactions.as_view(), name='get-transactions'),

    path('update_profile', UpdateAccountProfile.as_view(), name='update-account'),
]
