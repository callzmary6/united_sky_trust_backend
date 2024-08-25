from datetime import datetime, timedelta

from rest_framework import generics, status
from rest_framework.response import Response

from authentication.permissions import IsAuthenticated
from authentication.utils import Util as auth_util
from account_manager.utils import Util as manager_util

from .serializers import TransferSerializer, VirtualCardSerializer, FundVirtualCardSerializer, SupportTicketSerializer, ChequeDepositSerializer, CommentSerializer, RealCardSerializer, KYCSerializer
from .utils import Util as user_util
from united_sky_trust.base_response import BaseResponse

from django.conf import settings
from django.core.paginator import Paginator
from cloudinary.uploader import upload
import uuid
import pymongo
import re
from bson import ObjectId


db = settings.DB
client = settings.MONGO_CLIENT

responses = {
    'success': status.HTTP_200_OK,
    'failed': status.HTTP_400_BAD_REQUEST
}

class AccountManager:
    @staticmethod
    def get_account_manager():
        return db.account_user.find_one({'isAdmin': True})
    
class DahsboardView(generics.GenericAPIView):
    permission_class = [IsAuthenticated]
    def get(self, request):
        pass


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

        user['_id'] = str(user['_id'])
        user['account_manager_id'] = str(user['account_manager_id'])

        return BaseResponse.response(status=True, data=user, HTTP_STATUS=status.HTTP_200_OK)


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

        otp = auth_util.generate_number(6)

        if imf_code == user_data['imf_code']:
            db.account_user.update_one({'_id': user_id}, {'$set': {'is_verified_imf': True}})
            data = {
                'subject': 'Verify your otp',
                'body': f'{otp}',
                'to': user_data['email']
            }
            auth_util.email_send(data)
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
        sender = request.user
        data = request.data
        isFake = False

        # Gets the account_manager and sender
        account_manager = AccountManager.get_account_manager()
 
        amount = data['amount']
        account_number = data['account_number']
        bank_name = data['bank_name']
        bank_routing_number = data['bank_routing_number']
        account_number = data['account_number']
        account_holder = data['account_holder']
        description = data['description']
        auth_pin = data['auth_pin']

        # start transactions for users 
        if auth_pin == sender['cot_code']:
            with client.start_session() as session:
                with session.start_transaction():
                    sender_result = db.account_user.find_one_and_update({
                        '_id': sender['_id'], 'account_balance': {'$gte': amount}},
                        {'$inc': {'account_balance': -amount}, '$set': {'last_balance_update_time': datetime.now()}},
                        return_document=True,
                        session=session
                    )

                    ref_number = manager_util.generate_code()

                    # send debit email and sms functionality
                    
                    if not sender_result:
                        session.abort_transaction()
                        return Response({'status': 'failed', 'message': 'Insufficient Funds!'}, status=responses['failed'])
                    
                    createdAt = sender_result['last_balance_update_time']
                    
                    receiver_result = db.account_user.find_one_and_update(
                        {'account_number': account_number},
                        {'$inc': {'account_balance': amount}},
                        return_document= True,
                        session=session
                        )


                    # send credit email and sms functionality
                    
                    if receiver_result is None:
                        isFake = True
                        beneficiary_account_holder = account_holder
                    else:
                        beneficiary_account_holder = f"{receiver_result['first_name']} {receiver_result['middle_name']} {receiver_result['last_name']}"
                        
                    # create transaction records
                    # Sender Transaction
                    db.transactions.insert_one({
                        'type': 'Debit',
                        'amount': amount,
                        'scope': 'Local Transfer',
                        'description': description,
                        'account_user_id': sender['_id'],
                        'account_manager_id': account_manager['_id'],
                        'account_holder': beneficiary_account_holder,
                        'account_number': account_number,
                        'status': 'Completed',
                        'ref_number': ref_number,
                        'createdAt': createdAt,
                        'bank_name': bank_name,
                        'bank_routing_number': bank_routing_number,
                    }, session=session)

                    # Receiver Transaction
                    if isFake == False:
                        db.transactions.insert_one({
                            'type': 'Credit',
                            'amount': amount,
                            'scope': 'Local Transfer',
                            'description': description,
                            'account_user_id': receiver_result['_id'],
                            'account_manager_id': account_manager['_id'],
                            'account_number': sender_result['account_number'],
                            'bank_name': 'United Heritage Trust',
                            'status': 'Completed',
                            'ref_number': ref_number,
                            'createdAt': createdAt
                        }, session=session)

            return Response({'status': 'success', 'message': 'Transaction Successful'}, status=responses['success'])
        
        return Response({'status': 'failed', 'error': 'Auth_pin is incorrect!'}, status=responses['failed'])


class GetAccountSummary(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'transaction_user_id': user['_id']}

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
    
class VirtualCardRequest(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        serializer = VirtualCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_manager = AccountManager.get_account_manager()

        # use sessions here

        serializer.validated_data['virtualcard_user_id'] = user['_id']
        serializer.validated_data['phone_number'] = user['phone_number']
        serializer.validated_data['email'] = user['email']
        serializer.validated_data['account_manager_id'] = account_manager['_id']
        serializer.validated_data['first_name'] = user['first_name']
        serializer.validated_data['middle_name'] = user['middle_name']
        serializer.validated_data['last_name'] = user['last_name']
        prefix = serializer.check_card_type(serializer.validated_data['card_type'].lower())  
        serializer.validated_data['createdAt'] = datetime.now()
        serializer.validated_data['card_number'] = user_util.generate_card_number(12, prefix)
        serializer.validated_data['cvv'] = auth_util.generate_number(3)
        serializer.validated_data['valid_through'] = serializer.validated_data['createdAt'] + timedelta(days=1095)
        serializer.validated_data['status'] = 'Pending'
        virtual_card_data = serializer.save()

        # virtual_card = db.virtual_cards.find_one({'_id': virtual_card_data.inserted_id})

        data = {
            '_id': str(virtual_card_data.inserted_id),
            'card_type': serializer.validated_data['card_type'],
            'card_number': serializer.validated_data['card_number'],
            'valid_through': serializer.validated_data['valid_through'],
            'cvv': serializer.validated_data['cvv'],
            'balance': serializer.validated_data['balance'],
            'status': serializer.validated_data['status']
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
                        {'$inc': {'balance': amount}, '$set': {'last_fund_time': datetime.now()}},
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

    
class ChequeDepositRequest(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChequeDepositSerializer
    def post(self, request):
        user = request.user
        account_manager = AccountManager.get_account_manager()
        data = request.data
        
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data['first_name'] = user['first_name']
        serializer.validated_data['middle_name'] = user['middle_name']
        serializer.validated_data['last_name'] = user['last_name']
        serializer.validated_data['cheque_user_id'] = user['_id']
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
    
class LinkRealCard(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RealCardSerializer

    def post(self, request):
        user = request.user
        data = request.data
        account_manager = AccountManager.get_account_manager()

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['card_user_id'] = user['_id']
        serializer.validated_data['account_manager_id'] = account_manager['_id']
        serializer.save()

        return BaseResponse.response(status=True, message='Card linked!', HTTP_STATUS=status.HTTP_200_OK)
    
class GetRealLInkedCards(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        sorted_real_cards = db.real_cards.find({'card_user_id': user['_id']}, {'card_user_id': 0, 'account_manager_id': 0}).sort('createdAt', pymongo.DESCENDING)

        real_cards = []
        for real_card in sorted_real_cards:
            real_card['_id'] = str(real_card['_id'])
            real_cards.append(real_card)

        data = {
            'real_cards': real_cards,
            'no_of_real_cards': len(real_cards)
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)

class WireTransfer(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        data = request.data
        account_manager = AccountManager.get_account_manager()
        db.transactions.insert_one({
            'type': 'Debit',
            'amount': data['amount'],
            'scope': 'Wire Transfer',
            'description': data['description'],
            # 'account_currency': data['currency'],
            'transaction_user_id': user['_id'],
            'account_manager_id': account_manager['_id'],
            'account_holder': '',
            'status': 'Completed',
            'ref_number': manager_util.generate_code(),
            'createdAt': datetime.now(),
            'state_province': data['state_province'],
            'recipient_full_name': data['recepient_full_name'],
            'iban': data['iban'],
            'swift_code': data['swift_code'],
            'delivery_date': data['delivery_date'],
            'wire_type': data['type'],
            'delivery_data': data['delivery_date']
        })

        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
    
class ApplyKYC(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = KYCSerializer

    def post(self, request):
        user = request.user
        data = request.data
        account_manager = AccountManager.get_account_manager()

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['kyc_user_id'] = user['_id']
        serializer.validated_data['first_name'] = user['first_name']
        serializer.validated_data['middle_name'] = user['middle_name']
        serializer.validated_data['last_name'] = user['last_name']
        serializer.validated_data['email'] = user['email']

        serializer.validated_data['account_manager_id'] = account_manager['_id']
        serializer.save()

        return BaseResponse.response(status=True, message='Kyc applied successfully!', HTTP_STATUS=status.HTTP_200_OK)
    
class GetPastDebitCredit(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user

        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)

        query = {'account_user_id': user['_id'], 'createdAt': {'$gte': start_date, '$lte': end_date + timedelta(days=1)}}

        # Aggregate the shipment by date
        pipeline = [
            {'$match': query},
            {'$project': {"day": {"$dayOfWeek": "$createdAt"}, "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}}}},
            {"$group": {"_id": {"day": "$day", "date": "$date"}, "count": {"$sum": 1}}},
            {"$sort": {"_id.date": 1}}
        ]

        query['type'] = 'Credit'
        credits = list(db.transactions.aggregate(pipeline))

        query['type'] = 'Debit'
        debits = list(db.transactions.aggregate(pipeline))

        # Format the result
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

        credits_this_week = []
        debits_this_week = []

        day_count_1 = {(start_date + timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(7)}
        day_count_2 = {(start_date + timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(7)}


        for credit in credits:
            date_str = credit['_id']['date']
            day_count_1[date_str] = credit['count']

        for debit in debits:
            date_str = debit['_id']['date']
            day_count_2[date_str] = debit['count']

        for date_str, count in day_count_1.items():
            date = datetime.strptime(date_str, '%Y-%m-%d')
            day_index = (date.weekday() + 1) % 7
            day_name = days[day_index]
            formatted_result = {
                "day": day_name,
                "date": date.strftime("%d/%m/%Y"),
                "no_of_credits": count
            }
            credits_this_week.append(formatted_result)
        
        for date_str, count in day_count_2.items():
            date = datetime.strptime(date_str, '%Y-%m-%d')
            day_index = (date.weekday() + 1) % 7
            day_name = days[day_index]
            formatted_result = {
                "day": day_name,
                "date": date.strftime("%d/%m/%Y"),
                "no_of_debits": count
            }
            debits_this_week.append(formatted_result)


        data = {
            'Credits': credits_this_week,
            'Debits': debits_this_week,
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    



                  






                

    

    




        
            



       