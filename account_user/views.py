from datetime import datetime, timedelta

from rest_framework import generics, status
from rest_framework.response import Response

from authentication.permissions import IsAuthenticated
from authentication.utils import Util
from account_manager.utils import Util as manager_util

from .serializers import TransferSerializer, VirtualCardSerializer, FundVirtualCardSerializer, SupportTicketSerializer, ChequeDepositSerializer, CommentSerializer
from .utils import Util as user_util
from united_sky_trust.base_response import BaseResponse

from django.conf import settings
from cloudinary.uploader import upload
import uuid
import pymongo
from bson import ObjectId
from datetime import datetime

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

        sorted_transactions = sorted(transactions, key=lambda x: x['createdAt'], reverse=True)

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

class GetUserDetails(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user

        data = {
            '_id': str(user['_id']),
            'email': user['email'],
            'first_name': user['first_name'],
            'middle_name': user['middle_name'],
            'account_id': user['account_number'],
            'balance': user['account_balance'],
            'account_currency': user['account_currency'],
            'createdAt': user['createdAt']
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)


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

                    serializer.validated_data['ref_number'] = manager_util.generate_code()
                    serializer.validated_data['createdAt'] = sender_result['last_balance_update_time']

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
                        'createdAt': serializer.validated_data['createdAt'],
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
                        'createdAt': serializer.validated_data['createdAt']
                    }, session=session)

            return Response({'status': 'success', 'message': 'Transaction Successful'}, status=responses['success'])
        
        return Response({'status': 'failed', 'error': 'codes not verified'}, status=responses['failed'])


class GetUserTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        user = request.user

        query = {'transaction_user_id': str(user['_id'])}
        filter = {'_id': 1, 'ref_number': 1, 'amount': 1, 'status': 1, 'type': 1, 'description': 1, 'scope': 1, 'createdAt': 1}

        sorted_transaction = db.transactions.find(query, filter).sort('createdAt', pymongo.DESCENDING)

        list_transactions = []

        for transaction in sorted_transaction:
            transaction['_id']  = str(transaction['_id'])
            list_transactions.append(transaction)

        data = {
            'transactions': list_transactions,
            'total_transactions': len(list_transactions)
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    
class VirtualCardRequest(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, ]
    def post(self, request):
        user = request.user
        serializer = VirtualCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_manager = AccountManager.get_account_manager()

        # use sessions here

        serializer.validated_data['virtualcard_user_id'] = user['_id']
        serializer.validated_data['account_manager_id'] = account_manager['_id']
        serializer.validated_data['card_holder_name'] = f"{user['first_name']} {user['middle_name']} {user['last_name']}"
        virtual_card_data = serializer.save()

        virtual_card = db.virtual_cards.find_one({'_id': virtual_card_data.inserted_id})

        data = {
            'card_type': virtual_card['card_type'],
            'card_number': virtual_card['card_number'],
            'valid_through': virtual_card['valid_through'],
            'cvv': virtual_card['cvv'],
            'balance': virtual_card['balance'],
            'status': virtual_card['status']
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)

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
                    ref_number = manager_util.generate_code()
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
                        'createdAt': virtual_card_update['last_fund_time'],
                    }, session=session)

                    return Response({'status': 'success', 'updated_balance': virtual_card_update['balance']}, status=responses['success'])
        return Response({'status': 'failed', 'error': 'card is unavailable for funding!'}, status=responses['failed'])
    

class GetVirtualCards(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user

        virtual_cards_data = db.virtual_cards.find({'account_user_id': user['_id']}, {'security_question': 0, 'answer': 0, 'account_user_id': 0, 'account_manager_id': 0, 'last_fund_time': 0}).sort('createdAt', pymongo.DESCENDING)

        virtual_cards = list(virtual_cards_data)
        total_cards = len(virtual_cards)

        return Response({'status': 'success', 'virtual_cards': virtual_cards, 'total_virtual_cards': total_cards}, status=responses['success'])
    
class CreateSupportTicketView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer

    def post(self, request):
        user = request.user
        data = request.data
        
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data['support_user_id'] = user['_id']
        serializer.validated_data['account_manager_id'] = user['account_manager_id']
        serializer.validated_data['comments'] = []

        serializer.save()

        return Response({'status': 'success', 'message': 'Support ticket created!'}, status=responses['success'])
    
class CreateCommentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, support_ticket_id):
        user = request.user
        data  = request.data

        support_ticket = db.support_ticket.find_one({'support_user_id': user['_id'], '_id': ObjectId(support_ticket_id)})

        old_comments = support_ticket['comments']
        
        comment = db.comments.insert_one({
            'message': data['message'],
            'support_ticket_id': support_ticket['_id'],
            'comment_user_full_name': f"{user['first_name']} {user['middle_name']} {user['last_name']}",
            'sender_id': user['_id'],
            'receiver_id': user['account_manager_id'],
            'createdAt': datetime.now()
        })  

        new_comments = old_comments + [comment.inserted_id]  

        db.support_ticket.update_one({'_id': support_ticket['_id']}, {'$set': {'comments': new_comments}})

        return BaseResponse.response(status=True, message='Reply sent!', HTTP_STATUS=status.HTTP_200_OK)

    
class CheckDepositRequest(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChequeDepositSerializer
    def post(self, request):
        user = request.user
        account_manager = AccountManager.get_account_manager()
        data = request.data
        front_cheque = request.FILES['front_cheque']
        back_cheque = request.FILES['back_cheque']

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        front_cheque_data = upload(front_cheque, folder='cheques')
        back_cheque_data = upload(back_cheque,folder='cheques')

        serializer.validated_data['front_cheque'] = front_cheque_data['secure_url']
        serializer.validated_data['back_cheque'] = back_cheque_data['secure_url']
        serializer.validated_data['account_holder'] = f"{user['first_name']} {user['middle_name']} {user['last_name']}"
        serializer.validated_data['cheque_deposit_user_id'] = user['_id']
        serializer.validated_data['account_manager_id'] = account_manager['_id']
        serializer.validated_data['ref_number'] = manager_util.generate_code()
        serializer.validated_data['createdAt'] = datetime.now()
        cheque_data = serializer.save()

        db.transactions.insert_one({
            'type': 'Credit',
            'amount': serializer.validated_data['cheque_amount'],
            'scope': 'Cheque Deposit',
            'cheque_id': cheque_data.inserted_id,
            'description': 'Mobile Cheque Deposit',
            'account_user_id': user['_id'],
            'account_manager_id': user['account_manager_id'],
            'account_holder': f"{user['first_name']} {user['middle_name']} {user['last_name']}",
            'status': 'Pending',    
            'ref_number': serializer.validated_data['ref_number'],
            'createdAt': serializer.validated_data['createdAt'],
        })

        return BaseResponse.response(status=True, message='Check request pending', HTTP_STATUS=status.HTTP_200_OK)
    



                  






                

    

    




        
            



       