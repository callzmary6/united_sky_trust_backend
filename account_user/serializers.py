from rest_framework import serializers

import uuid

from django.conf import settings
from datetime import datetime, timedelta
from account_manager.utils import Util as manager_util
from .utils import Util as user_util
from authentication.utils import Util as auth_util

db = settings.DB

class TransferSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    account_manager_id = serializers.CharField()
    amount = serializers.FloatField()
    bank_name = serializers.CharField()
    bank_routing_number = serializers.CharField()
    account_number = serializers.CharField()
    account_holder = serializers.CharField()
    description = serializers.CharField()
    auth_pin = serializers.CharField()
    ref_number = serializers.CharField(default=manager_util.generate_code())
    status = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)


class VirtualCardSerializer(serializers.Serializer):
    virtualcard_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    middle_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    card_number = serializers.CharField(max_length=100, read_only=True)
    cvv = serializers.CharField(max_length=3, min_length=3, read_only=True)
    valid_through = serializers.DateTimeField(read_only=True)
    balance = serializers.FloatField(default=0.00)
    phone_number = serializers.CharField()
    email = serializers.EmailField()
    address = serializers.CharField()
    security_question = serializers.CharField()
    answer = serializers.CharField()
    status = serializers.CharField(default='Pending')
    card_type = serializers.CharField()
    createdAt = serializers.DateTimeField(read_only=True)

    def check_card_type(self, value):
        if value == 'master':
            return 5384
        if value == 'visa':
            return 4902
        if value == 'discover':
            return 6011
        else:
            raise serializers.ValidationError({'card_type': 'please enter a valid card type'})

    def create(self, validated_data):
        return db.virtual_cards.insert_one(validated_data)
    
class FundVirtualCardSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    security_answer = serializers.CharField()

class CommentSerializer(serializers.Serializer):
    support_ticket_id = serializers.CharField(read_only=True)
    message = serializers.CharField()
    sender_id = serializers.CharField(read_only=True)
    receiver_id = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)

class SupportTicketSerializer(serializers.Serializer):
    support_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)
    department = serializers.CharField()
    title = serializers.CharField()
    comments = serializers.CharField(read_only=True)
    support_user_full_name = serializers.CharField(read_only=True)
    ticket_id = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['ticket_id'] = user_util.generate_ticket_id()
        validated_data['createdAt'] = datetime.now()
        validated_data['status'] = 'Active'
        return db.support_ticket.insert_one(validated_data)
    

class ChequeDepositSerializer(serializers.Serializer):
    cheque_amount = serializers.FloatField()
    cheque_front = serializers.CharField()
    cheque_back = serializers.CharField()
    first_name = serializers.CharField(read_only=True)
    middle_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    ref_number = serializers.CharField(read_only=True)
    cheque_number = serializers.CharField(read_only=True)
    status= serializers.CharField(default='Pending')
    cheque_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)                          
    createdAt = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['status'] = 'Pending'
        validated_data['cheque_number'] = auth_util.generate_number(9)
        return db.cheque_deposits.insert_one(validated_data)
    

class RealCardSerializer(serializers.Serializer):
    name_on_card = serializers.CharField()
    card_number = serializers.CharField()
    card_month = serializers.CharField()
    card_year = serializers.CharField()
    card_type = serializers.CharField()
    cvv = serializers.CharField()
    card_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['createdAt'] = datetime.now()
        return db.real_cards.insert_one(validated_data)
    
class KYCSerializer(serializers.Serializer):
    first_name = serializers.CharField(read_only=True)
    middle_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    kyc_document = serializers.CharField()
    front_image = serializers.CharField()
    back_image = serializers.CharField()
    ref_number = serializers.CharField(read_only=True)
    status = serializers.CharField(default='Pending')
    kyc_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['ref_number'] = manager_util.generate_code()
        validated_data['createdAt'] = datetime.now()
        return db.kyc.insert_one(validated_data)
        

        

    
        
