from rest_framework import serializers

from django.conf import settings
import uuid

from .utils import Util
from datetime import datetime

db = settings.DB

class TransactionSerializer(serializers.Serializer):
    transaction_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)
    ref_number = serializers.CharField(read_only=True)
    account_holder = serializers.CharField(read_only=True)
    type = serializers.CharField()
    amount = serializers.FloatField()
    scope = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField(read_only=True)
    account_currency = serializers.CharField()
    send_email= serializers.BooleanField()
    createdAt = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        db.transactions.insert_one(validated_data)
        return validated_data
