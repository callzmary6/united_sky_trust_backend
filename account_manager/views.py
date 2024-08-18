from rest_framework import generics, status
from rest_framework.response import Response

from authentication.permissions import IsAuthenticated
from authentication.serializers import AccountManagerSerializer
from .serializers import TransactionSerializer
from united_sky_trust.base_response import BaseResponse
from .utils import Util as manager_util

from django.conf import settings
from django.core.paginator import Paginator
import re
import pymongo
from pymongo import ReturnDocument
from bson import ObjectId
import datetime

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
        user_id = request.user['_id']
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'account_manager_id': str(user_id)}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'first_name': search_regex},
                {'middle_name': search_regex},
                {'last_name': search_regex},
                {'account_number': search_regex},
                {'account_balance': search_regex},
            ]
        
        users = db.account_user.find(query, {'first_name': 1, 'middle_name': 1, 'last_name': 1, 'email': 1, 'account_balance': 1, 'account_number': 1, 'isVerified': 1, 'createdAt': 1, 'isSuspended': 1, 'isTransferBlocked': 1})

        total_users = db.account_user.count_documents(query)

        sorted_users = sorted(users, key=lambda x: x['createdAt'], reverse=True)

        list_users = []
        
        for user in sorted_users:
            user['_id'] = str(user['_id'])
            list_users.append(user)

        paginator = Paginator(list_users, entry)
        page_obj = paginator.get_page(page)

        new_users = list(page_obj)
        
        data = {
            'registered_users': new_users,
            'total_account_users': total_users,
            'current_page': page
        }

        return BaseResponse.response(
            status=True,
            HTTP_STATUS=status.HTTP_200_OK,
            data=data
        )
    
class GetUserDetail(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        account_manager = request.user
        except_fields = {'password': 0, 'is_verified_cot': 0, 'is_verified_imf': 0, 'is_verified_otp': 0, 'is_authenticated': 0, 'full_name': 0}
        account_user = db.account_user.find_one({'_id': ObjectId(id), 'account_manager_id': str(account_manager['_id'])}, except_fields)
        if account_user is None:
            return BaseResponse.response(status=False, message='User does not exist!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
        account_user['_id'] = str(account_user['_id'])
        return BaseResponse.response(status=True, data=account_user, HTTP_STATUS=status.HTTP_200_OK)


class FundAccount(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class= TransactionSerializer
    def post(self, request, acn):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            account_user = db.account_user.find_one({'account_number': acn, 'account_manager_id': str(user['_id'])})
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

            serializer.validated_data['transaction_user_id'] = str(account_user['_id'])
            serializer.validated_data['account_manager_id'] = str(user['_id'])
            serializer.validated_data['account_holder'] = f"{account_user['first_name']} {account_user['middle_name']} {account_user['last_name']}"
            serializer.validated_data['status'] = 'Completed'
            serializer.validated_data['account_currency'] = account_user['account_currency']
            serializer.validated_data['ref_number'] = manager_util.generate_code()
            serializer.validated_data['createdAt'] = datetime.datetime.now()
            serializer.save()
            
            db.transactions.insert_one({
                    'type': 'Credit',
                    'amount': serializer.validated_data['amount'],
                    'scope': 'Local Transfer',
                    'description': serializer.validated_data['description'],
                    'frequency': 1,
                    'transaction_user_id': account_user['_id'],
                    'account_manager_id': user['_id'],
                    'account_holder': f"{account_user['first_name']} {account_user['middle_name']} {account_user['last_name']}",
                    'account_currency': serializer.validated_data['account_currency'],
                    'account_number': acn,
                    'status': 'Completed',
                    'ref_number': serializer.validated_data['ref_number'],
                    'createdAt': serializer.validated_data['createdAt'],
                    })

            # Send email functionality

            return BaseResponse.response(status=True, data={'new_account_balance': new_account_balance}, HTTP_STATUS=status.HTTP_200_OK)#
        return BaseResponse.response(status=False, data=serializer.errors, HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
    

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
            query['$or'] = [
                {'ref_number': search_regex},
                {'account_holder': search_regex},
                {'amount': search_regex},
                {'description': search_regex},
                {'type': search_regex},
                {'scope': search_regex},
                {'status': search_regex},
            ]

        sorted_transactions = db.transactions.find(query, {'ref_number': 1, 'account_holder': 1, 'amount': 1, 'description': 1, 'type': 1, 'scope': 1, 'status': 1, 'createdAt': 1}).sort('createdAt', pymongo.DESCENDING)

        total_transactions = db.transactions.count_documents(query)

        # paginate the transactions
        paginator = Paginator(list(sorted_transactions), entry)
        transactions_per_page = paginator.get_page(page)

        new_transactions = []
        for transaction in transactions_per_page:
            transaction['_id'] = str(transaction['_id'])
            new_transactions.append(transaction)

        data = {
            'transactions': new_transactions,
            'no_of_transactions': total_transactions,
            'current_page': page
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    
class AccountUserTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]
    def get(self, request, id):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')
        user_id = str(user['_id'])

        query = {'transaction_user_id': id, 'account_manager_id': user_id}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'ref_number': search_regex},
                {'account_holder': search_regex},
                {'amount': search_regex},
                {'description': search_regex},
                {'type': search_regex},
                {'scope': search_regex},
                {'status': search_regex},
            ]

        sorted_transactions = db.transactions.find(query, {'ref_number': 1, 'account_holder': 1, 'amount': 1, 'description': 1, 'type': 1, 'scope': 1, 'account_currency': 1, 'status': 1, 'createdAt': 1}).sort('createdAt', pymongo.DESCENDING)

        total_transactions = db.transactions.count_documents(query)

        # paginate the transactions
        paginator = Paginator(list(sorted_transactions), entry)
        transactions_per_page = paginator.get_page(page)

        new_transactions = []
        for transaction in transactions_per_page:
            transaction['_id'] = str(transaction['_id'])
            new_transactions.append(transaction)

        data = {
            'transactions': new_transactions,
            'no_of_transactions': total_transactions,
            'current_page': page
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)

class UpdateTransactionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]
    serializer_class = TransactionSerializer

    def patch(self, request, id):
        user = request.user
        serializer = self.serializer_class(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        query = {'_id': ObjectId(id), 'account_manager_id': user['_id']}
        update_fields = {'$set': serializer.validated_data}
        try:
            updated_transaction = db.transactions.find_one_and_update(query, update_fields, return_document=ReturnDocument.AFTER)
            if updated_transaction==None:
                return BaseResponse.response(status=False, message='Transaction does not exist!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
            return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
        except Exception as e:
            return BaseResponse.response(status=False, data=str(e), HTTP_STATUS=status.HTTP_400_BAD_REQUEST)

        
class DeleteTransaction(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, id):
        user = request.user
        db.transactions.delete_one({'_id': ObjectId(id), 'account_manager_id': user['_id']})
        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
    
class UpdateAccountProfile(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        data = request.data
        serializer = AccountManagerSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        query = {'_id': ObjectId(request.user['_id'])}
        update_field = {'$set': serializer.validated_data}
        db.account_user.find_one_and_update(query, update_field, return_document=ReturnDocument.AFTER)
        return Response({'status': 'success'}, status=responses['success'])
    
# Virtual Card Functionlity
class GetVirtualCards(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'account_manager_id': user['_id']}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'card_holder_name': search_regex},
                {'card_type': search_regex},
                {'card_number': search_regex},
                {'cvv': search_regex},
                {'valid_through': search_regex},
                {'status': search_regex}
            ]

        filter = {'card_holder_name': 1, 'card_type': 1, 'balance': 1, 'card_number': 1, 'cvv': 1, 'valid_through': 1, 'status': 1}

        sorted_virtual_cards = db.virtual_cards.find(query, filter).sort('createdAt', pymongo.DESCENDING)

        paginator = Paginator(list(sorted_virtual_cards), entry)
        virtual_card_per_page = paginator.get_page(page)

        virtual_cards = []

        for virtual_card in virtual_card_per_page:
            virtual_card['_id'] = str(virtual_card['_id'])
            virtual_cards.append(virtual_card)

        total_virtual_card = len(virtual_cards)

        data = {
            'virtual_cards': virtual_cards,
            'total_virtual_cards': total_virtual_card,
            'current_page': page
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    
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
    
class GetChequeDeposits(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'account_manager_id': str(user['_id'])}
        display_fields = {'ref_number': 1, 'account_holder': 1, 'amount': 1, 'cheque_number': 1, 'status': 1, 'createdAt': 1, 'status': 1}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'ref_number': search_regex},
                {'amount': search_regex},
                {'cheque_number': search_regex},
                {'status': search_regex},
                {'account_holder': search_regex}
            ]

        sorted_deposit_cheques = db.cheque_deposits.find(query, display_fields).sort('createdAt', pymongo.DESCENDING)

        paginator = Paginator(list(sorted_deposit_cheques), entry)
        deposit_cheques_per_page = paginator.get_page(page)

        deposit_cheques = []
        for deposit_cheque in deposit_cheques_per_page:
            deposit_cheque['_id'] = str(deposit_cheque['_id'])
            deposit_cheques.append(deposit_cheque)

        total_deposit_cheque = len(deposit_cheques)

        data = {
            'deposit_cheques': deposit_cheques,
            'total_deposit_cheques': total_deposit_cheque,
            'current_page': page
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)

    







    
    

    


            

        







