from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('authentication/', include('authentication.urls')),
    path('acct_manager/', include('account_manager.urls')),
    path('acct_user/', include('account_user.urls')),
]
