from rest_framework import serializers
from django.conf import settings

from .utils import Util

from datetime import datetime

db = settings.DB

class AccountManagerSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=15)
    last_name = serializers.CharField(max_length=15)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    is_authenticated = serializers.CharField(default=True, read_only=True)

    def create(self, validated_data):
        account_manager = db.account_manager.insert_one(validated_data)
        return account_manager
    
class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

class AccountUserSerializer(serializers.Serializer):
    account_manager_id = serializers.CharField(read_only=True)
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=64)
    middle_name = serializers.CharField(max_length=64)
    last_name = serializers.CharField(max_length=64)
    fullname = serializers.CharField(read_only=True)
    country = serializers.CharField()
    state = serializers.CharField()
    city = serializers.CharField()
    zip_code = serializers.CharField()
    date_of_birth = serializers.CharField()
    house_address = serializers.CharField()
    account_number = serializers.CharField(read_only=True)
    account_type = serializers.CharField()
    account_currency = serializers.CharField()
    account_balance = serializers.DecimalField(default=0.00, decimal_places=2, max_digits=12)
    imf_code = serializers.CharField()
    cot_code = serializers.CharField()
    two_factor_pin = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    is_authenticated = serializers.CharField(default=True)
    date_created = serializers.CharField(read_only=True)
    status = serializers.CharField(default='Active')
    is_verified = serializers.BooleanField(default=False)

    def validate(self, attrs):
        password = attrs.get('password', '')
        password2 = attrs.get('password2', '')

        if password != password2:
            raise serializers.ValidationError({'error': 'password mismatch!'})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        validated_data['account_number'] = Util.generate_number(11)
        validated_data['two_factor_pin'] = Util.generate_number(4)
        validated_data['date_created'] = datetime.now()
        validated_data['full_name'] = f"{validated_data['first_name']} {validated_data['middle_name']} {validated_data['last_name']}"
        
        account_user = db.account_user.insert_one(validated_data)
        validated_data['id'] = str(account_user.inserted_id)
        return validated_data
    
class PasswordResetSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
        













