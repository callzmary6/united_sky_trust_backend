from rest_framework import generics, status
from rest_framework.response import Response

from authentication.permissions import IsAuthenticated
from authentication.serializers import AccountManagerSerializer
from .serializers import TransactionSerializer
from united_sky_trust.base_response import BaseResponse
from .utils import Util as manager_util
from authentication.utils import Util as auth_util

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

        query = {'account_manager_id': user_id}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'first_name': search_regex},
                {'middle_name': search_regex},
                {'last_name': search_regex},
                {'account_number': search_regex},
                {'account_balance': search_regex},
            ]
        
        sorted_users = db.account_user.find(query, {'is_authenticated': 0, 'password': 0, 'account_manager_id': 0, 'is_verified_otp': 0, 'is_verified_cot': 0, 'is_verified_imf': 0}).sort('createdAt', pymongo.DESCENDING)

        paginator = Paginator(list(sorted_users), entry)
        page_obj = paginator.get_page(page)

        new_users = []

        for user in page_obj:
            user['_id'] = str(user['_id'])
            new_users.append(user)

        total_users = len(new_users)
        
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
    def post(self, request, user_id): 
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            account_user = db.account_user.find_one({'_id': ObjectId(user_id), 'account_manager_id': user['_id']})

            with client.start_session() as session:
                with session.start_transaction(): 
                    amount = serializer.validated_data['amount']
                    if serializer.validated_data['type'].lower() == 'credit':
                        account_user = db.account_user.find_one_and_update({'_id': ObjectId(user_id), 'account_manager_id': user['_id']}, {'$inc': {'account_balance': amount}})

                        serializer.validated_data['transaction_user_id'] = account_user['_id']
                        serializer.validated_data['account_manager_id'] = user['_id']
                        serializer.validated_data['account_holder'] = f"{account_user['first_name']} {account_user['middle_name']} {account_user['last_name']}"
                        serializer.validated_data['status'] = 'Completed'
                        serializer.validated_data['ref_number'] = manager_util.generate_code()
                        serializer.validated_data['createdAt'] = datetime.datetime.now()
                        serializer.save()

                        if serializer.validated_data['send_email'] == True:
                            data = {
                                'subject': 'Account Credited',
                                'body': f"Your account has been credited with {amount}{account_user['account_currency']}",
                                'to': account_user['email']
                            }
                            auth_util.email_send(data)
                            # send sms functionality
                        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
                    
                    if serializer.validated_data['type'].lower() == 'debit':
                        if account_user['account_balance'] < serializer.validated_data['amount']:
                            session.abort_transaction()
                            return BaseResponse.response(status=False, message='Insufficient Funds!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
                        
                        db.account_user.find_one_and_update({'_id': ObjectId(user_id), 'account_manager_id': user['_id']}, {'$inc': {'account_balance': -amount}})
                        
                        serializer.validated_data['transaction_user_id'] = account_user['_id']
                        serializer.validated_data['account_manager_id'] = user['_id']
                        serializer.validated_data['account_holder'] = f"{account_user['first_name']} {account_user['middle_name']} {account_user['last_name']}"
                        serializer.validated_data['status'] = 'Completed'
                        serializer.validated_data['ref_number'] = manager_util.generate_code()
                        serializer.validated_data['createdAt'] = datetime.datetime.now()
                        serializer.save()

                        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)   
        return BaseResponse.response(status=False, data=serializer.errors, HTTP_STATUS=status.HTTP_400_BAD_REQUEST)

class GetTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated,]
    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')
        user_id = user['_id']

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
                {'status': search_regex},
            ]

        filter = {'card_holder_name': 1, 'card_type': 1, 'balance': 1, 'card_number': 1, 'cvv': 1, 'valid_through': 1, 'createdAt': 1, 'virtualcard_user_id':  1, 'status': 1}

        sorted_virtual_cards = db.virtual_cards.find(query, filter).sort('createdAt', pymongo.DESCENDING)

        paginator = Paginator(list(sorted_virtual_cards), entry)
        virtual_card_per_page = paginator.get_page(page)

        virtual_cards = []

        for virtual_card in virtual_card_per_page:
            virtual_card['_id'] = str(virtual_card['_id'])
            virtual_card['virtualcard_user_id'] = str(virtual_card['virtualcard_user_id'])
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
        status = 'Pending'
        query = {'_id': ObjectId(vc_id), 'account_manager_id': user['_id'], 'status': status}
        virtual_card = db.virtual_cards.find_one_and_update(query, {'$set': {'status': 'Active'}})
        if virtual_card is None:
            query['status'] = 'Active'
            virtual_card = db.virtual_cards.find_one_and_update(query, {'$set': {'status': status}})
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

        query = {'account_manager_id': user['_id']}
        display_fields = {'ref_number': 1, 'first_name': 1, 'middle_name': 1, 'last_name': 1, 'amount': 1, 'cheque_number': 1, 'cheque_currency': 1, 'status': 1, 'createdAt': 1}

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
    
class GetKYC(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'account_manager_id': user['_id']}
        display_fields = {'kyc_user_id': 1, 'ref_number': 1, 'first_name': 1, 'middle_name': 1, 'last_name': 1, 'email': 1, 'kyc_document': 1, 'kyc_image': 1, 'status': 1, 'createdAt': 1}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'ref_number': search_regex},
                {'first_name': search_regex},
                {'last_name': search_regex},
                {'middle_name': search_regex},
            ]

        sorted_kycs = db.kyc.find(query, display_fields).sort('createdAt', pymongo.DESCENDING)

        paginator = Paginator(list(sorted_kycs), entry)
        kyc_per_page = paginator.get_page(page)

        kycs = []
        for kyc in kyc_per_page:
            kyc['_id'] = str(kyc['_id'])
            kyc['kyc_user_id'] = str(kyc['kyc_user_id'])
            kycs.append(kyc)

        total_kycs = len(kycs)

        data = {
            'kycs': kycs,
            'total_kycs': total_kycs,
            'current_page': page
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    

class ApproveChequeDeposit(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, cheque_id):
        user = request.user
        cheque_deposits = db.cheque_deposits.find_one({'_id': ObjectId(cheque_id), 'account_manager_id': user['_id']})
        with client.start_session() as session:
            with session.start_transaction():
                if cheque_deposits['status'] == 'Pending':
                    db.account_user.find_one_and_update({'_id': cheque_deposits['cheque_user_id']}, {'$inc': {'account_balance': cheque_deposits['amount']}}, session=session)
                    db.cheque_deposits.find_one_and_update({'_id': ObjectId(cheque_id)}, {'$set': {'status': 'Completed'}}, session=session)
                    # send email functionality
                    return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
                else:
                    db.cheque_deposits.find_one_and_update({'_id': ObjectId(cheque_id)}, {'$set': {'status': 'Pending'}}, session=session)
                    return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
            
class DeleteChequeDeposit(generics.GenericAPIView):
    def delete(self, request, cheque_id):
        user = request.user
        db.cheque_deposits.delete_one({'_id': ObjectId(cheque_id), 'account_manager_id': user['_id']})
        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)

class ApproveKYC(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, kyc_id):
        user = request.user
        kyc = db.kyc.find_one({'_id': ObjectId(kyc_id), 'account_manager_id': user['_id']})

        with client.start_session() as session:
            with session.start_transaction():
                if kyc['status'] == 'Pending':
                    db.kyc.update_one({'_id': ObjectId(kyc_id), 'account_manager_id': user['_id']}, {'$set': {'status': 'Completed'}}, session=session)
                    db.account_user.find_one_and_update({'_id': kyc['kyc_user_id']}, {'$set': {'isTransferBlocked': False}}, session=session)
                else:
                    db.kyc.update_one({'_id': ObjectId(kyc_id), 'account_manager_id': user['_id']}, {'$set': {'status': 'Pending'}}, session=session)
                    db.account_user.find_one_and_update({'_id': kyc['kyc_user_id']}, {'$set': {'isTransferBlocked': True}}, session=session)
                # send email functionality
                return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
                
class DeleteKYC(generics.GenericAPIView):
    def delete(self, request, kyc_id):
        user = request.user
        db.kyc.delete_one({'_id': ObjectId(kyc_id), 'account_manager_id': user['_id']})
        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)


class WireTransfer(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        data = request.data
        db.transactions.insert_one({
            'type': 'Debit',
            'amount': data['amount'],
            'scope': 'Wire Transfer',
            'description': '',
            'account_currency': data['currency'],
            'transaction_user_id': '',
            'account_manager_id': user['_id'],
            'account_holder': '',
            'status': 'Completed',
            'ref_number': manager_util.generate_code(),
            'createdAt': datetime.datetime.now()
        })

        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)

class GetTotalRegisteredUsers(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        total_users = db.account_user.count_documents({'account_manager_id': user['_id']})
        return BaseResponse.response(status=True, data={'total_users': total_users},HTTP_STATUS=status.HTTP_200_OK)
    
class GetTotalTransactions(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        total_transactions = db.transactions.count_documents({'account_manager_id': user['_id']})
        return BaseResponse.response(status=True, data={'total_transactions': total_transactions},HTTP_STATUS=status.HTTP_200_OK)
    
class GetTotalChequeDeposits(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        total_cheque_deposits = db.cheque_deposits.count_documents({'account_manager_id': user['_id']})
        return BaseResponse.response(status=True, data={'total_cheque_deposits': total_cheque_deposits},HTTP_STATUS=status.HTTP_200_OK)
    
class GetTotalUnverifiedUsers(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        total_unverified_users = db.account_user.count_documents({'account_manager_id': user['_id'], 'isVerified': False})
        return BaseResponse.response(status=True, data={'total_unverified_users': total_unverified_users},HTTP_STATUS=status.HTTP_200_OK)


class GetChartData(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user

        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=6)

        query = {'account_manager_id': user['_id'], 'createdAt': {'$gte': start_date, '$lte': end_date + datetime.timedelta(days=1)}}

        transactions_this_week = db.transactions.count_documents(query)
        users_this_week = db.account_user.count_documents(query)

        data = {
            'transactions_this_week': transactions_this_week,
            'users_this_week': users_this_week
        }
        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    
class GetCurrencyChartData(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        query = {'account_manager_id': user['_id'],}
        
        pipeline = [
                {'$match': query},
                {'$group': {'_id': '$account_currency', 'total_users': {'$sum': 1}}}
        ]

        results = db.account_user.aggregate(pipeline)

        new_results = []

        for result in results:
            if result['_id'] == None:
                continue
            new_results.append(result)

        return BaseResponse.response(status=True, data=new_results, HTTP_STATUS=status.HTTP_200_OK)

class SendCustomEmail(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        data = request.data

        email_data = {
            'subject': data['subject'],
            'body': data['message'],
            'to': data['email']
        }

        auth_util.email_send(email_data)

        return BaseResponse.response(status=True, HTTP_STATUS=status.HTTP_200_OK)
    
class CreateCommentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, support_ticket_id):
        user = request.user
        data  = request.data

        support_ticket = db.support_ticket.find_one({'account_manager_id': user['_id'], '_id': ObjectId(support_ticket_id)})

        old_comments = support_ticket['comments']
        
        comment = db.comments.insert_one({
            'message': data['message'],
            'support_ticket_id': support_ticket['_id'],
            'sender_id': user['_id'],
            'receiver_id': ObjectId(support_ticket['support_user_id']),
            'comment_user_full_name': 'Customer Care',
            'createdAt': datetime.datetime.now()
        })

        new_comments = old_comments + [comment.inserted_id]  

        db.support_ticket.update_one({'_id': support_ticket['_id']}, {'$set': {'comments': new_comments}})

        return BaseResponse.response(status=True, message='Reply sent!', HTTP_STATUS=status.HTTP_200_OK)
    
class GetComments(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, support_ticket_id):
        user = request.user
        support_ticket = db.support_ticket.find_one({'account_manager_id': user['_id'], '_id': ObjectId(support_ticket_id)})
        
        comment_obj = db.comments.find({'support_ticket_id': ObjectId(support_ticket_id), '_id': {'$in': support_ticket['comments']}}, {'support_ticket_id': 0, 'sender_id': 0, 'receiver_id': 0}).sort('createdAt', pymongo.ASCENDING)

        comments = []

        for comment in comment_obj:
            comment['_id'] = str(comment['_id'])
            comments.append(comment)

        data = {
            'ticket_id': support_ticket['ticket_id'],
            'comments': comments,
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)
    
class GetSupportTicket(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        entry = int(request.GET.get('entry', 10))
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '')

        query = {'account_manager_id': user['_id']}
        display_fields = {'_id': 1, 'department': 1, 'ticket_id': 1, 'createdAt': 1, 'comments': 1, 'status': 1}

        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            query['$or'] = [
                {'ticket_id': search_regex},
                {'department': search_regex},
                {'date': search_regex},
                {'status': search_regex},
            ]

        sorted_support_tickets = db.support_ticket.find(query, display_fields).sort('createdAt', pymongo.DESCENDING)

        paginator = Paginator(list(sorted_support_tickets), entry)
        support_ticket_per_page = paginator.get_page(page)

        support_tickets = []

        for support_ticket in support_ticket_per_page:
            support_ticket['_id'] = str(support_ticket['_id'])
            support_ticket['comments'] = len(support_ticket['comments'])
            support_tickets.append(support_ticket)

        total_support_tickets = len(support_tickets)

        data = {
            'support_tickets': support_tickets,
            'total_support_ticket': total_support_tickets,
            'current_page': page
        }

        return BaseResponse.response(status=True, data=data, HTTP_STATUS=status.HTTP_200_OK)


    

    

    





        
        
    

                


    







    
    

    


            

        







