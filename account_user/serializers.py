from rest_framework import serializers

import uuid

from django.conf import settings
from datetime import datetime, timedelta
from account_manager.utils import Util as manager_util
from .utils import Util as user_util
from authentication.utils import Util as auth_util

db = settings.DB

class TransferSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    user_id = serializers.UUIDField()
    account_manager_id = serializers.UUIDField()
    amount = serializers.FloatField()
    bank_name = serializers.CharField()
    bank_routing_number = serializers.CharField()
    account_number = serializers.CharField()
    account_holder = serializers.CharField()
    beneficiary_account_holder = serializers.CharField()
    description = serializers.CharField()
    ref_number = serializers.CharField(default=manager_util.generate_code())
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class VirtualCardSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    account_user_id = serializers.UUIDField(read_only=True)
    account_manager_id = serializers.UUIDField(read_only=True)
    card_holder_name = serializers.CharField(max_length=255, read_only=True)
    card_number = serializers.CharField(max_length=100, read_only=True)
    cvv = serializers.CharField(max_length=3, min_length=3, read_only=True)
    valid_through = serializers.DateTimeField(read_only=True)
    balance = serializers.FloatField(default=0.00)
    phone_number = serializers.CharField(max_length=20)
    email_address = serializers.EmailField()
    address = serializers.CharField()
    security_question = serializers.CharField()
    answer = serializers.CharField()
    card_type = serializers.CharField()
    is_activated = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)

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
        validated_data['card_type'] = validated_data['card_type'].lower()

        prefix = self.check_card_type(validated_data['card_type'])  

        validated_data['created_at'] = datetime.now()
        validated_data['card_number'] = user_util.generate_card_number(12, prefix)
        validated_data['cvv'] = auth_util.generate_number(3)
        validated_data['valid_through'] = validated_data['created_at'] + timedelta(days=1095)

        return db.virtual_cards.insert_one(validated_data)
    
class FundVirtualCardSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    amount = serializers.FloatField()
    security_answer = serializers.CharField()

class SupportTicketSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    account_user_id = serializers.UUIDField(read_only=True)
    account_manager_id = serializers.UUIDField(read_only=True)
    department = serializers.CharField()
    complaints = serializers.CharField()
    ticket_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['ticket_id'] = user_util.generate_ticket_id()
        validated_data['created_at'] = datetime.now()
        return db.support_ticket.insert_one(validated_data)
    

class CommentSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    support_ticket_id = serializers.UUIDField()
        

    
        
