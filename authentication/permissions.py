from rest_framework import permissions
from django.contrib.auth.models import AnonymousUser


class IsAuthenticated(permissions.BasePermission):
    # Allows access to only authenticated users

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return bool(request.user and request.user.is_authenticated)
        else:
            return bool(request.user and request.user['is_authenticated'])