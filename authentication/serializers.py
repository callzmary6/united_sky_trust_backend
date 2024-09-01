from rest_framework import serializers
from django.conf import settings

from .utils import Util
import uuid

from datetime import datetime

db = settings.DB

class AccountManagerSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=15)
    middle_name= serializers.CharField(max_length=20)
    last_name = serializers.CharField(max_length=15)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    is_admin = serializers.CharField(default=True)
    role = serializers.CharField(read_only=True)
    is_authenticated = serializers.CharField(default=True)
    createdAt = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['createdAt'] = datetime.now()
        validated_data['role'] = 'Admin'
        account_manager = db.account_user.insert_one(validated_data)
        return account_manager
    
class LoginAdminSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email', '')
        password = attrs.get('password', '')

        errors = {}

        if email == '' and password == '':
            errors['email'] = 'email should not be empty!'
            errors['password'] = 'password should not be empty!'

        if email == '':
            errors['email'] = 'email should not be empty!'

        if password == '':
            errors['password'] = 'password should not be empty!'

        if errors:
            raise serializers.ValidationError(errors)

class LoginAccountUserSerializer(serializers.Serializer):
    account_id = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

class AccountUserSerializer(serializers.Serializer):
    account_manager_id = serializers.CharField(read_only=True)
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField()
    state_province = serializers.CharField()
    last_name = serializers.CharField()
    zip_code_postal_code = serializers.CharField()
    date_of_birth = serializers.CharField()
    country = serializers.CharField()
    city = serializers.CharField()
    house_address = serializers.CharField()
    account_number = serializers.CharField(read_only=True)
    account_type = serializers.CharField()
    account_currency = serializers.CharField()
    account_balance = serializers.FloatField(default=0.00)
    imf_code = serializers.CharField()
    cot_code = serializers.CharField()
    auth_pin = serializers.CharField()
    password = serializers.CharField(write_only=True)
    is_authenticated = serializers.CharField(default=True)
    createdAt = serializers.CharField(read_only=True)
    isVerified = serializers.BooleanField(default=False)
    # is_two_factor = serializers.BooleanField(default=False)
    isSuspended = serializers.BooleanField(default=False)
    isTransferBlocked = serializers.BooleanField(default=True)
    isAdmin = serializers.BooleanField(default=False)
    role = serializers.CharField(read_only=True)
    annual_income_range = serializers.CharField(default='')
    occupation = serializers.CharField(default='')
    profile_picture = serializers.URLField(default='')
    is_verified_cot = serializers.BooleanField(default=False)
    is_verified_imf = serializers.BooleanField(default=False)
    is_verified_otp = serializers.BooleanField(default=False)


    def create(self, validated_data):
        email = validated_data['email']
        phone_number = validated_data['phone_number']
        validated_data['account_number'] = Util.generate_number(11)
        validated_data['role'] = 'User'
        validated_data['profile_picture'] = ''
        validated_data['createdAt'] = datetime.now()

        if db.account_user.find_one({'email': email}):
            raise serializers.ValidationError({'error': {'email': 'Email is already in use!'}})
        
        if db.account_user.find_one({'phone_number': phone_number}):
            raise serializers.ValidationError({'error':{'phone_number': 'Phone number is already in use!'}})
        
        return db.account_user.insert_one(validated_data)
    
class PasswordResetSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

        













