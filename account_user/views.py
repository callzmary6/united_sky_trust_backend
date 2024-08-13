from datetime import datetime, timedelta

from rest_framework import generics, status
from rest_framework.response import Response

from authentication.permissions import IsAuthenticated
from authentication.utils import Util
from account_manager import utils

from .serializers import TransferSerializer, VirtualCardSerializer, FundVirtualCardSerializer, SupportTicketSerializer
from .utils import Util as user_util

from django.conf import settings
import uuid
import pymongo
import datetime

db = settings.DB
client = settings.MONGO_CLIENT

responses = {
    'success': status.HTTP_200_OK,
    'failed': status.HTTP_400_BAD_REQUEST
}

class AccountManager:
    @staticmethod
    def get_account_manager():
        return db.account_user.find_one({'is_admin': True})


class GetTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    def get(self, request):
        user = request.user

        all_transactions = []
        credit = []
        debit = []

        transactions = db.transactions.find({'account_user_id': user['_id']})

        sorted_transactions = sorted(transactions, key=lambda x: x['created_at'], reverse=True)

        for transaction in sorted_transactions:
            all_transactions.append(transaction)

            if transaction['type'] == 'Credit':
                credit.append(transaction)
            if transaction['type'] == 'Debit':
                debit.append(transaction)

        return Response({
            'status': 'success',
            'transactions': {
                'all': all_transactions,
                'credit': credit,
                'debit': debit,
            },
        }, status=responses['success'])
    
class GetPercentageExpenses(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        account_user_transactions = db.transactions.find({'account_user_id': user['_id']})

        transactions = list(account_user_transactions)
        total_expenses = len(transactions)
        total_debit = 0
        total_credit = 0

        for transaction in transactions:
            if transaction['type'].lower() == 'credit':
                total_credit += 1
            if transaction['type'].lower() == 'debit':
                total_debit += 1

        percentage_credit = float((total_credit / total_expenses) * 100)
        percentage_debit = float((total_debit / total_expenses) * 100)

        return Response({
            'status': 'success',
            'percentage_credit': percentage_credit,
            'percentage_debit': percentage_debit,
        }, status=responses['success'])

    
class VerifyCOTCode(generics.GenericAPIView):
    def post(self, request):
        user_id = request.user['_id']
        cot_code = request.data.get('cot_code', '')

        user_data = db.account_user.find_one({'_id': user_id})

        if cot_code == user_data['cot_code']:
            db.account_user.update_one({'_id': user_id}, {'$set': {'is_verified_cot': True}})
            return Response({'status': 'success', 'message': 'cot code verified successfully!'}, status=responses['success'])
        else:
            return Response({'status': 'failed', 'error': 'cot vode is not correct'}, status=responses['failed'])
              
class VerifyIMFCode(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user_id = request.user['_id']
        imf_code = request.data.get('imf_code', '')
        user_data = db.account_user.find_one({'_id': user_id})

        otp = Util.generate_number(6)

        if imf_code == user_data['imf_code']:
            db.account_user.update_one({'_id': user_id}, {'$set': {'is_verified_imf': True}})
            data = {
                'subject': 'Verify your otp',
                'body': f'{otp}',
                'to': user_data['email']
            }
            Util.email_send(data)
            expire_at = datetime.now() + timedelta(seconds=300)
            db.otp_codes.insert_one({'_id': uuid.uuid4().hex[:24], 'user_id': user_data['_id'], 'code': otp, 'expireAt': expire_at})
            return Response({'status': 'success', 'message': 'cot code verified successfully, An otp has been sent to your email!'}, status=responses['success'])
        else:
            return Response({'status': 'failed', 'error': 'imf code is not correct'}, status=responses['failed'])

class OTPVerifyView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    def post(self, request):
        user_id = request.user['_id']
        otp = request.data.get('otp', '')
        user_otp = db.otp_codes.find_one({'user_id': user_id, 'code': otp})

        if user_otp == None:
            return Response({'status': 'failed', 'error': 'Invalid OTP'}, status=responses['failed'])
        
        db.account_user.update_one({'_id': user_id}, {'$set': {'is_verified_otp': True}})
        return Response({'status': 'success', 'message': 'otp verified'}, status=responses['success'])
    
class CheckAccountBalance(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user_id = request.user['_id']
        amount = request.data.get('amount', '')
        user_data = db.account_user.find_one({'_id': user_id, 'account_balance': {'$gte': float(amount)}})

        if user_data is None:
            return Response({'status': 'failed', 'error': 'Insufficient Funds!', 'account_balance': request.user['account_balance']}, status=responses['failed'])
        
        return Response({'status': 'success', 'balance': request.user['account_balance']}, status=responses['success'])       

class TransferFundsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    serializer_class = TransferSerializer

    def post(self, request):
        user = request.user
        data = request.data
        
        serializer = self.serializer_class(data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Gets the account_manager and sender
        account_manager = AccountManager.get_account_manager()
        sender = db.account_user.find_one({'_id': user['_id']})

        # Checks if the cot, imf and otp have been verified
        if sender['is_verified_cot'] == True and sender['is_verified_imf'] == True and sender['is_verified_otp'] == True:
            amount = serializer.validated_data['amount']
            account_number = serializer.validated_data['account_number']

            # start transactions for users 
            with client.start_session() as session:
                with session.start_transaction():
                    sender_result = db.account_user.find_one_and_update({
                        '_id': user['_id'], 'account_balance': {'$gte': amount}},
                        {'$inc': {'account_balance': -amount}, '$set': {'is_verified_cot': False, 'is_verified_imf': False, 'is_verified_otp': False, 'last_balance_update_time': datetime.datetime.now()}},
                        return_document=True,
                        session=session
                    )

                    serializer.validated_data['ref_number'] = utils.Util.generate_code()
                    serializer.validated_data['created_at'] = sender_result['last_balance_update_time']

                    # send debit email and sms functionality
                    
                    if not sender_result:
                        session.abort_transaction()
                        return Response({'status': 'failed', 'message': 'Insufficient Funds!'}, status=responses['failed'])
                    
                    receiver_result = db.account_user.find_one_and_update(
                        {'account_number': account_number},
                        {'$inc': {'account_balance': amount}},
                        return_document= True,
                        session=session
                        )
                    
                    serializer.validated_data['beneficiary_account_holder'] = receiver_result['full_name']

                    # send credit email and sms functionality
                    
                    if not receiver_result:
                        session.abort_transaction()
                        return Response({'status': 'failed', 'message': 'User not found!'}, status=responses['failed'])
                    
                    # create transaction records
                    # Sender Transaction
                    db.transactions.insert_one({
                        '_id': uuid.uuid4().hex[:24],
                        'type': 'Debit',
                        'amount': amount,
                        'scope': 'Local Transfer',
                        'description': serializer.validated_data['description'],
                        'frequency': 1,
                        'account_user_id': user['_id'],
                        'account_manager_id': account_manager['_id'],
                        'account_holder': receiver_result['full_name'],
                        'account_number': account_number,
                        'status': 'Completed',
                        'ref_number': serializer.validated_data['ref_number'],
                        'created_at': serializer.validated_data['created_at'],
                        # 'bank_name': serializer.validated_data['bank_name'],
                        'bank_routing_number': serializer.validated_data['bank_routing_number'],
                        'beneficiary_account_holder': receiver_result['full_name']
                    }, session=session)

                    # Receiver Transaction
                    db.transactions.insert_one({
                        '_id': uuid.uuid4().hex[:24],
                        'type': 'Credit',
                        'amount': amount,
                        'scope': 'Local Transfer',
                        'description': serializer.validated_data['description'],
                        'frequency': 1,
                        'account_user_id': receiver_result['_id'],
                        'account_manager_id': account_manager['_id'],
                        'account_holder': user['full_name'],
                        'account_number': sender_result['account_number'],
                        # 'bank_name': '',
                        'status': 'Completed',
                        'ref_number': serializer.validated_data['ref_number'],
                        'created_at': serializer.validated_data['created_at']
                    }, session=session)

            return Response({'status': 'success', 'message': 'Transaction Successful'}, status=responses['success'])
        
        return Response({'status': 'failed', 'error': 'codes not verified'}, status=responses['failed'])


class GetUserTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        user = request.user

        query = {'account_user_id': user['_id']}
        filter = {'ref_number': 1, 'amount': 1, 'status': 1, 'type': 1, 'description': 1, 'scope': 1, 'created_at': 1}

        transaction_data = db.transactions.find(query, filter).sort('created_at', pymongo.DESCENDING)

        transactions = list(transaction_data)

        return Response({'status': 'success', 'transactions': transactions, 'total_transactions': len(transactions)}, status=responses['success'])
    
class VirtualCardRequest(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    def post(self, request):
        user = request.user
        serializer = VirtualCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_manager = AccountManager.get_account_manager()

        # use sessions here

        serializer.validated_data['account_user_id'] = user['_id']
        serializer.validated_data['account_manager_id'] = account_manager['_id']
        serializer.validated_data['card_holder_name'] = user['full_name']
        virtual_card_data = serializer.save()

        virtual_card = db.virtual_cards.find_one({'_id': virtual_card_data.inserted_id})
        

        db.security_questions.insert_one({
        '_id': uuid.uuid4().hex[:24],
        'question': virtual_card['security_question'],
        'answer': virtual_card['answer'],
        'account_user_id': virtual_card['_id'],
        'account_manager_id': virtual_card['account_manager_id']
        })

        return Response({
            'status': 'success',
            'card_type': virtual_card['card_type'],
            'card_number': virtual_card['card_number'],
            'valid_through': virtual_card['valid_through'],
            'cvv': virtual_card['cvv'],
            'balance': virtual_card['balance'],
            'is_active': virtual_card['is_activated']
            },
            status=responses['success']
            )

class FundVirtualCard(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, vc_id):
        user = request.user
        data = request.data
        serializer = FundVirtualCardSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        query = {'_id': vc_id, 'account_user_id': user['_id']}
        virtual_card = db.virtual_cards.find_one(query)
        
        if virtual_card['is_activated'] == True:
            with client.start_session() as session:
                with session.start_transaction():
                    ref_number = utils.Util.generate_code()
                    description = user_util.generate_formatted_code()
                    security_answer = serializer.validated_data['security_answer']
                    amount = serializer.validated_data['amount']

                    account_user = db.account_user.find_one({'_id': user['_id'], 'account_balance': {'$gte': amount}}, session=session)

                    if account_user == None:
                        session.abort_transaction()
                        return Response({'status': 'failed', 'error': 'Insufficient Balance'}, status=responses['failed'])
                    
                    if security_answer != virtual_card['answer']:
                        session.abort_transaction()
                        return Response({'status': 'failed', 'error': 'security answer is not correct!'}, status=responses['failed'])
                    
                    virtual_card_update = db.virtual_cards.find_one_and_update(query,
                        {'$inc': {'balance': amount}, '$set': {'last_fund_time': datetime.datetime.now()}},
                        return_document=True,
                        session=session
                    )
                    db.transactions.insert_one({
                        '_id': uuid.uuid4().hex[:24],
                        'type': 'Debit',
                        'amount': amount,
                        'scope': 'VirtualCard Top-up',
                        'description': description,
                        'frequency': 1,
                        'account_user_id': user['_id'],
                        'account_manager_id': user['account_manager_id'],
                        'account_holder': user['full_name'],
                        'account_number': user['account_number'],
                        'status': 'Completed',
                        'ref_number': ref_number,
                        'created_at': virtual_card_update['last_fund_time'],
                    }, session=session)

                    return Response({'status': 'success', 'updated_balance': virtual_card_update['balance']}, status=responses['success'])
        return Response({'status': 'failed', 'error': 'card is unavailable for funding!'}, status=responses['failed'])
    

class GetVirtualCards(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user

        virtual_cards_data = db.virtual_cards.find({'account_user_id': user['_id']}, {'security_question': 0, 'answer': 0, 'account_user_id': 0, 'account_manager_id': 0, 'last_fund_time': 0}).sort('created_at', pymongo.DESCENDING)

        virtual_cards = list(virtual_cards_data)
        total_cards = len(virtual_cards)

        return Response({'status': 'success', 'virtual_cards': virtual_cards, 'total_virtual_cards': total_cards}, status=responses['success'])
    
class SupportTicketView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer

    def post(self, request):
        user = request.user
        data = request.data
        
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data['account_user_id'] = user['_id']
        serializer.validated_data['account_manager_id'] = user['account_manager_id']
        serializer.save()

        return Response({'status': 'success', 'message': 'support ticket created'}, status=responses['success'])
                






                

    

    




        
            



       