from django.urls import path

from .views import RegisterAccountManager, LoginAccountManager

urlpatterns = [
    path('register', RegisterAccountManager.as_view(), name='register'),
    path('login', LoginAccountManager.as_view(), name='login'),
]
