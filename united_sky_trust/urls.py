from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('authentication/', include('authentication.urls')),
    path('acct_manager/', include('account_manager.urls')),
    path('acct_user/', include('account_user.urls')),

] + debug_toolbar_urls()

