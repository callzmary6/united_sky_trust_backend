from rest_framework import serializers

import uuid

from django.conf import settings
from datetime import datetime, timedelta
from account_manager.utils import Util
from authentication import utils

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
    ref_number = serializers.CharField(default=Util.generate_code())
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

    def create(self, validated_data):
        validated_data['created_at'] = datetime.now()
        validated_data['card_number'] = utils.Util.generate_number(16)
        validated_data['cvv'] = utils.Util.generate_number(3)
        validated_data['valid_through'] = validated_data['created_at'] + timedelta(days=1095)

        return db.virtual_cards.insert_one(validated_data)
    
class FundVirtualCardSerializer(serializers.Serializer):
    _id = serializers.UUIDField(default=uuid.uuid4().hex[:24])
    amount = serializers.FloatField()
    security_answer = serializers.CharField()
    
        
