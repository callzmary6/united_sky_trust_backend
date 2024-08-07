from rest_framework import serializers

import uuid

from django.conf import settings
from datetime import datetime
from account_manager.utils import Util

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

    # def create(self, validated_data):
    #     validated_data['created_at'] = datetime.now()
    #     transfers = db.transfers.insert_one(validated_data)
    #     return validated_data
