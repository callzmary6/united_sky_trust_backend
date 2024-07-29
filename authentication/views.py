from rest_framework import generics, status
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from .serializers import AccountManagerSerializer, LoginAdminSerializer, AccountUserSerializer, PasswordResetSerializer, LoginAccountUserSerializer

from .authentications import JWTAuthentication
from .permissions import IsAuthenticated
from .utils import Util

from bson import ObjectId
from cloudinary.uploader import upload
from datetime import datetime, timedelta

db = settings.DB

class RegisterAccountManager(generics.GenericAPIView):
    def post(self, request):
        serializer = AccountManagerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': {'email': serializer.validated_data['email'], 'first_name': serializer.validated_data['first_name'], 'last_name': serializer.validated_data['last_name']}}, status=status.HTTP_201_CREATED)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class LoginAccountManager(generics.GenericAPIView):
    serializer_class = LoginAdminSerializer
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        errors = {}
        responses = {
            'success': status.HTTP_200_OK,
            'failed': status.HTTP_400_BAD_REQUEST
        }

        if not email and not password:
            errors['email'] = 'email should not be empty'
            errors['password'] = 'password should not be empty'
        if not email:
            errors['email'] = 'email should not be empty'
        if not password:
            errors['password'] = 'password should not be empty'

        if errors:
            return Response(errors, status=responses['failed'])
        
        user = db.account_user.find_one({'email': email, 'password': password})
        
        if not user:
            return Response({'status': 'failed', 'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)
        
        token = JWTAuthentication.create_jwt(user)

        # users = db.account_user.find({'account_user_id': str(user['_id'])})

        return Response({
            'status': 'success',
            'message': 'You have logged in successfully',
            'access_token': token,
            'users': {
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name']
        }
    })

class CreateAccountUser(generics.GenericAPIView):
    serializer_class = AccountUserSerializer
    # permission_classes = [IsAuthenticated,]
    def post(self, request):
        data = request.data
        user = request.user
        if isinstance(user, AnonymousUser):
            user = db.account_user.find_one({'is_admin': True})
        profile_picture = request.data.get('profile_picture')
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.validated_data['account_manager_id'] = str(user['_id'])
            upload_result = upload(profile_picture)
            serializer.validated_data['profile_picture'] = upload_result['secure_url']
            user_data = serializer.save()

            # Email Functionality
            code = Util.generate_number(6)
            db.otp_codes.create_index('expireAt', expireAfterSeconds=120)
            expire_at = datetime.utcnow() + timedelta(seconds=120)
            db.otp_codes.insert_one({'user_id': user_data['_id'], 'code': code, 'expireAt': expire_at})
            data = {
                'subject': 'Email Confirmation',
                'to': user_data['email'],
                'body': f'Use this otp to verify your account {code}'
            }
            Util.email_send(data)

            return Response({
                'status': 'success',
                'user_data': {
                    'id': str(user_data['id']),
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'account_number': user_data['account_number'],
                    'profile_picture': user_data['profile_picture']
                }
            }, status=status.HTTP_201_CREATED)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

class LoginAccountUser(generics.GenericAPIView):
    def post(self, request):
        account_id  = request.data.get('account_id')
        password = request.data.get('password')

        errors = {}
        responses = {
            'success': status.HTTP_200_OK,
            'failed': status.HTTP_400_BAD_REQUEST
        }

        if not account_id and not password:
            errors['email'] = 'account_id should not be empty'
            errors['password'] = 'password should not be empty'
        if not account_id:
            errors['email'] = 'account_id should not be empty'
        if not password:
            errors['password'] = 'password should not be empty'

        if errors:
            return Response(errors, status=responses['failed'])
        
        account_user = db.account_user.find_one({'account_number': account_id, 'password': password})

        if not account_user:
            return Response({'status': 'failed', 'error': 'Invalid Credentials!'}, status=responses['failed'])
        
        if account_user['is_suspended'] == False:

            if account_user['is_two_factor'] == True:
                two_factor_code = Util.generate_number(4)
                expire_at = datetime.utcnow() + timedelta(seconds=120)
                db.otp_codes.insert_one({'user_id': account_user['_id'], 'code': two_factor_code, 'expireAt': expire_at})
                data = {
                    'subject': 'Two Factor Authentication',
                    'to': account_user['email'],
                    'body': f'Use this otp to verify your login {two_factor_code}'
                }
                Util.email_send(data)
                return Response({'status': 'success', 'message': 'check your email for 2fa code'}, status=responses['success'])

            token = JWTAuthentication.create_jwt(account_user)

            all_transactions = []
            credit = []
            debit = []
            transactions = db.transactions.find({'account_user_id': str(account_user['_id'])})

            sorted_transactions = sorted(transactions, key=lambda x: x['created_at'], reverse=True)

            for transaction in sorted_transactions:
                transaction['_id'] = str(transaction['_id'])
                all_transactions.append(transaction)

                if transaction['type'] == 'Credit':
                    transaction['_id'] = str(transaction['_id'])
                    credit.append(transaction)
                if transaction['type'] == 'Debit':
                    transaction['_id'] = str(transaction['_id'])
                    debit.append(transaction)


            return Response({
                'status': 'success',
                'token': token,
                'user_data': {
                    'full_name': account_user['full_name'],
                    'account_balance': account_user['account_balance'],
                    'profile_picture': account_user['profile_picture'],
                    'transactions': {
                        'all': all_transactions,
                        'credit': credit,
                        'debit': debit,
                    },
                    'account_type': account_user['account_type']
                }
            }, status=responses['success'])
        return Response({'status': 'failed', 'error': 'Account is suspended'}, status=responses['failed'])


class VerifyAccountUser(generics.GenericAPIView):
    def post(self, request, user_id):
        code = request.data.get('code')
        user_code = db.otp_codes.find_one({'user_id': ObjectId(user_id)})
        
        if not user_code:
            return Response({'status': 'failed', 'error': 'code has expired'}, status=status.HTTP_400_BAD_REQUEST)
        if  code != user_code['code']:
            return Response({'status': 'failed', 'error': 'code is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            db.account_user.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_verified': True}})
            return Response({'status': 'success', 'message': 'Code is verified'}, status=status.HTTP_200_OK)
        
class GenerateOTPCode(generics.GenericAPIView):
    def get(self, request, user_id, no_otp):
        user_data = db.account_user.find_one({'_id': ObjectId(user_id)})
        code = Util.generate_number(int(no_otp))
        expire_at = datetime.utcnow() + timedelta(seconds=120)
        db.otp_codes.insert_one({'user_id': user_data['_id'], 'code': code, 'expireAt': expire_at})
        data = {
            'to': user_data['email'],
            'body': f'Use this otp to verify your account {code}'
        }
        Util.email_send(data)
        return Response({'status': 'success', 'otp_code': code})


class PasswordResetView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordResetSerializer
    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            account_user = db.account_user.find_one({'_id': user['_id']})
            if serializer.validated_data['old_password'] != account_user['password']:
                return Response({'status': 'failed', 'error': 'Password is not correct!'}, status=status.HTTP_400_BAD_REQUEST)
            if serializer.validated_data['new_password'] != serializer.validated_data['confirm_password']:
                return Response({'status': 'failed', 'error': 'Passwords mismatch!'}, status=status.HTTP_400_BAD_REQUEST)
            
            db.account_user.update_one({'_id': user['_id']}, {'$set': {'password': serializer.validated_data['new_password']}})
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

class SuspendAccountUser(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, acc_id):
        account_user = db.account_user.find_one({'_id': ObjectId(acc_id)})
        if account_user['is_suspended'] == True:
            update = {'$set': {'is_suspended': False, 'status': 'Active'}}
            db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
            return Response({'status:': 'success', 'message': 'Account is active'}, status=status.HTTP_200_OK)

        update = {'$set': {'is_suspended': True, 'status': 'Suspended'}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
        return Response({'status:': 'success', 'message': 'Account is suspended'}, status=status.HTTP_200_OK)
    

class ApproveAccountUser(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, acc_id):
        update = {'$set': {'is_approved': True}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
    

class TwoFactorAuthentication(generics.GenericAPIView):
    permission_classes= [IsAuthenticated]
    def post(self, request, acc_id):
        account_user = db.account_user.find_one({'_id': ObjectId(acc_id)})
        if account_user['is_two_factor'] == False:
            update = {'$set': {'is_two_factor': True}}
            db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
            return Response({'status:': 'success', 'message': 'two factor enabled'}, status=status.HTTP_200_OK)
        
        update = {'$set': {'is_two_factor': False}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
        return Response({'status:': 'success', 'message': 'two factor disabled'}, status=status.HTTP_200_OK)
        

    

    
    
            


        


            

        


