from rest_framework import serializers
from django.conf import settings

from .authentications import JWTAuthentication

db = settings.DB

class AccountManagerSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    email = serializers.CharField(required=True)
    first_name = serializers.CharField(max_length=15)
    last_name = serializers.CharField(max_length=15)
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        account_manager = db.account_manager.insert_one(validated_data)
        return account_manager
    
class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)


