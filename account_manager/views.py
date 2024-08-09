from rest_framework import generics, status
from rest_framework.response import Response

from authentication.permissions import IsAuthenticated
from authentication.serializers import AccountManagerSerializer
from .serializers import TransactionSerializer

from django.conf import settings
from django.core.paginator import Paginator
import re
import pymongo
from pymongo import ReturnDocument

db = settings.DB
client = settings.MONGO_CLIENT

responses = {
    'success': status.HTTP_200_OK,
    'failed': status.HTTP_400_BAD_REQUEST
}


class Transactions:
    @staticmethod
    def get_all_transactions():
        return db.transactions.find({})

class GetRegisteredUsers(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_id = str(request.user['_id'])
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'account_manager_id': user_id}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'full_name': search_regex},
                {'account_number': search_regex},
                {'account_balance': search_regex},
            ]
        
        users = db.account_user.find(query, {'full_name': 1, 'email': 1, 'account_balance': 1, 'account_number': 1, 'is_verified': 1, 'date_created': 1, 'status': 1})

        total_users = db.account_user.count_documents(query)

        sorted_users = sorted(users, key=lambda x: x['date_created'], reverse=True)

        paginator = Paginator(list(sorted_users), entry)
        page_obj = paginator.get_page(page)

        new_users = list(page_obj)

        return Response({'status': 'success', 'registered_users': new_users, 'total_account_users': total_users, 'current_page': page}, status=status.HTTP_200_OK)
    
class FundAccount(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class= TransactionSerializer
    def post(self, request, acn):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            account_user = db.account_user.find_one({'account_number': acn})
            new_account_balance = account_user['account_balance']
            if serializer.validated_data['type'] == 'credit' or serializer.validated_data['type'] == 'Credit':
                for i in range(serializer.validated_data['frequency']):
                    new_account_balance += serializer.validated_data['amount']
            else:
                if account_user['account_balance'] < serializer.validated_data['amount']:
                    return Response({'status': 'failed', 'error': 'Insufficient Funds'}, status=status.HTTP_400_BAD_REQUEST)
                for i in range(serializer.validated_data['frequency']):
                    new_account_balance -= serializer.validated_data['amount']

            db.account_user.update_one({'account_number': acn}, {'$set':{'account_balance': new_account_balance}})

            serializer.validated_data['account_user_id'] = str(account_user['_id'])
            serializer.validated_data['account_manager_id'] = str(user['_id'])
            serializer.validated_data['account_holder'] = account_user['full_name']
            serializer.validated_data['status'] = 'Completed'
            serializer.save()
            # Send email functionality

            return Response({'status': 'success', 'new_account_balance': new_account_balance}, status=status.HTTP_200_OK)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

class GetTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]
    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')
        user_id = str(user['_id'])

        query = {'account_manager_id': user_id}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = {
                {'ref_number': search_regex},
                {'account_holder': search_regex},
                {'amount': search_regex},
                {'description': search_regex},
                {'type': search_regex},
                {'scope': search_regex},
                {'status': search_regex},
            }

        transactions = db.transactions.find(query, {'ref_number': 1, 'account_holder': 1, 'amount': 1, 'description': 1, 'type': 1, 'scope': 1, 'status': 1, 'created_at': 1})

        total_transactions = db.transactions.count_documents(query)

        sorted_transactions = sorted(transactions, key=lambda x: x['created_at'], reverse=True)

        # paginate the transactions
        paginator = Paginator(list(sorted_transactions), entry)
        transactions_per_page = paginator.get_page(page)

        new_transactions = []
        for transaction in transactions_per_page:
            transaction['_id'] = str(transaction['_id'])
            new_transactions.append(transaction)

        return Response({'status': 'success', 'transactions': new_transactions, 'no_of_transactions': total_transactions, 'current_page': page}, status=status.HTTP_200_OK)


class UpdateAccountProfile(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        data = request.data
        serializer = AccountManagerSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        query = {'_id': request.user['_id']}
        update_field = {'$set': serializer.validated_data}
        db.account_user.find_one_and_update(query, update_field, return_document=ReturnDocument.AFTER)
        return Response({'status': 'success'}, status=responses['success'])
    
# Virtual Card Functionlity
class GetVirtualCards(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        query = {'account_manager_id': user['_id']}

        filter = {'card_holder_name': 1, 'card_type': 1, 'balance': 1, 'card_number': 1, 'cvv': 1, 'valid_through': 1, 'is_activated': 1}

        virtual_cards_obj = db.virtual_cards.find(query, filter).sort('created_at', pymongo.DESCENDING)

        virtual_cards = list(virtual_cards_obj)

        return Response({
            'status': 'success',
            'virtual_cards': virtual_cards
        }, status=responses['success'])
    
class ActivateVirtualCard(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, vc_id):
        user = request.user
        is_activated = False
        query = {'_id': vc_id, 'account_manager_id': user['_id'], 'is_activated': is_activated}
        virtual_card = db.virtual_cards.find_one_and_update(query, {'$set': {'is_activated': True}})
        if virtual_card is None:
            query['is_activated'] = True
            virtual_card = db.virtual_cards.find_one_and_update(query, {'$set': {'is_activated': False}})
            # send email functionality
            return Response({'status': 'success', 'message': 'virtual card deactivated'}, status=responses['success'])
        return Response({'status': 'success', 'message': 'virtual card activated'}, status=responses['success'])
    







    
    

    


            

        







