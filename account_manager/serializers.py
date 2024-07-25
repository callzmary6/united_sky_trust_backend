from rest_framework import serializers

from django.conf import settings

from .utils import Util
from datetime import datetime

db = settings.DB

class TransactionSerializer(serializers.Serializer):
    account_user_id = serializers.CharField(read_only=True)
    account_manager_id = serializers.CharField(read_only=True)
    ref_number = serializers.CharField(read_only=True)
    account_holder = serializers.CharField(read_only=True)
    type = serializers.CharField(max_length=20)
    amount = serializers.FloatField()
    scope = serializers.CharField(max_length=20)
    description = serializers.CharField()
    frequency = serializers.IntegerField(default=1)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        validated_data['ref_number'] = Util.generate_code()
        validated_data['created_at'] = datetime.now()
        transaction = db.transactions.insert_one(validated_data)
        return validated_data
