from rest_framework import serializers
from django.conf import settings

from .utils import Util
import uuid

from datetime import datetime

db = settings.DB

class AccountManagerSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=15)
    middle_name= serializers.CharField(max_length=20)
    last_name = serializers.CharField(max_length=15)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    is_admin = serializers.CharField(default=True)
    is_authenticated = serializers.CharField(default=True)

    def create(self, validated_data):
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
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    account_manager_id = serializers.CharField(read_only=True)
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
    is_approved = serializers.BooleanField(default=False)
    is_two_factor = serializers.BooleanField(default=False)
    is_suspended = serializers.BooleanField(default=False)
    occupation = serializers.CharField()
    annual_income_range = serializers.CharField()
    ssn = serializers.CharField()
    is_admin = serializers.BooleanField(default=False)
    profile_picture = serializers.URLField(read_only=True)
    is_verified_cot = serializers.BooleanField(default=False)
    is_verified_imf = serializers.BooleanField(default=False)
    is_verified_otp = serializers.BooleanField(default=False)

    def validate(self, attrs):
        password = attrs.get('password', '')
        password2 = attrs.get('password2', '')

        if password != password2:
            raise serializers.ValidationError({'error': 'password mismatch!'})
        
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        phone_number = validated_data['phone_number']

        validated_data.pop('password2')
        validated_data['account_number'] = Util.generate_number(11)
        validated_data['two_factor_pin'] = Util.generate_number(4)
        validated_data['date_created'] = datetime.now()
        validated_data['full_name'] = f"{validated_data['first_name']} {validated_data['middle_name']} {validated_data['last_name']}"

        if db.account_user.find_one({'email': email}):
            raise serializers.ValidationError({'error': {'email': 'Email is already in use!'}})
        if db.account_user.find_one({'phone_number': phone_number}):
            raise serializers.ValidationError({'error':{'phone_number': 'Phone number is already in use!'}})
        
        account_user = db.account_user.insert_one(validated_data)
        return validated_data
    
class PasswordResetSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

        













