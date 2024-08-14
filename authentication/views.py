from rest_framework import generics, status
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from .serializers import AccountManagerSerializer, LoginAdminSerializer, AccountUserSerializer, PasswordResetSerializer, LoginAccountUserSerializer

from .authentications import JWTAuthentication
from .permissions import IsAuthenticated
from .utils import Util
from united_sky_trust.base_response import BaseResponse

from bson import ObjectId
from cloudinary.uploader import upload
from datetime import datetime, timedelta
import jwt

db = settings.DB
            
class Transactions:
    @staticmethod
    def get_all_transactions():
        return list(db.transactions.find({}, {'_id': 0}))
    

class RegisterAccountManager(generics.GenericAPIView):
    def post(self, request):
        serializer = AccountManagerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            data = {
                'email': serializer.validated_data['email'],
                'first_name': serializer.validated_data['first_name'],
                'middle_name': serializer.validated_data['middle_name'],
                'last_name': serializer.validated_data['last_name'] 
            }

            return BaseResponse.response(status=True, message='account created succesfully', data=data, HTTP_STATUS=status.HTTP_201_CREATED)
        return BaseResponse.response(status=False, message=serializer.errors, HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
        
    
class CheckToken(generics.GenericAPIView):
    def get(self, request, token):

        try:
            jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return BaseResponse.response(status=True, message='token is valid', HTTP_STATUS=status.HTTP_200_OK)
        except Exception as e:
            return BaseResponse.response(status=False, message=str(e), HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
    
class LoginAccountManager(generics.GenericAPIView):
    serializer_class = LoginAdminSerializer
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        errors = {}

        if not email and not password:
            errors['email'] = 'Email should not be empty!'
            errors['password'] = 'Password should not be empty!'
        if not email:
            errors['email'] = 'Email should not be empty!'
        if not password:
            errors['password'] = 'Password should not be empty!'

        if errors:
            return BaseResponse.response(
                status=False,
                message=errors,
                HTTP_STATUS=status.HTTP_400_BAD_REQUEST
            )
        
        user = db.account_user.find_one({'email': email, 'password': password})
        
        if not user:
            return BaseResponse.response(
                status=False,
                message='Invalid Credentials!',
                HTTP_STATUS=status.HTTP_400_BAD_REQUEST
            )

        token = JWTAuthentication.create_jwt(user)
        
        data = {
            'access_token': token,
            'users': {
                'email': user['email'],
                'first_name': user['first_name'],
                'middle_name': user['middle_name'],
                'last_name': user['last_name']
            }
        }

        return BaseResponse.response(
            status=True,
            message='You have logged in successfully',
            data=data,
            HTTP_STATUS=status.HTTP_201_CREATED
        )

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
            serializer.validated_data['account_manager_id'] = user['_id']
            upload_result = upload(profile_picture)
            serializer.validated_data['profile_picture'] = upload_result['secure_url']
            user_data = serializer.save()

            # Email Functionality
            code = Util.generate_number(6)
            db.otp_codes.create_index('expireAt', expireAfterSeconds=120)
            expire_at = datetime.now() + timedelta(seconds=120)
            db.otp_codes.insert_one({'user_id': user_data['_id'], 'code': code, 'expireAt': expire_at})
            data = {
                'subject': 'Email Confirmation',
                'to': user_data['email'],
                'body': f'Use this otp to verify your account {code}'
            }
            Util.email_send(data)

            data = {
                'user_data': {
                    '_id': user_data['_id'],
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'account_number': user_data['account_number'],
                    'profile_picture': user_data['profile_picture']
                }
            }

            return BaseResponse.response(status=True, message='account created successfully', data=data, HTTP_STATUS=status.HTTP_201_CREATED)

        return BaseResponse.response(status=False, message=serializer.errors, HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
    

class LoginAccountUser(generics.GenericAPIView):
    def post(self, request):
        account_id  = request.data.get('account_id')
        password = request.data.get('password')

        errors = {}

        if not account_id and not password:
            errors['account_id'] = 'Account_id should not be empty!'
            errors['password'] = 'Password should not be empty!'
        if not account_id:
            errors['email'] = 'Account_id should not be empty!'
        if not password:
            errors['password'] = 'Password should not be empty!'

        if errors:
            return BaseResponse.response(status=False, message=errors, HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
        
        account_user = db.account_user.find_one({'account_number': account_id, 'password': password})

        if not account_user:
            return BaseResponse.response(status=False, message='Invalid Credentials!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
        
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
                return BaseResponse.response(status=True, message='check your email for 2fa code', HTTP_STATUS=status.HTTP_201_CREATED)

            token = JWTAuthentication.create_jwt(account_user)
          
            return BaseResponse.response(
                status=True,
                data={
                'token': token,
                'user_data': {
                    'full_name': account_user['full_name'],
                    'account_balance': account_user['account_balance'],
                    'profile_picture': account_user['profile_picture'],
                    'account_type': account_user['account_type']
                }},
                message='account created successfully',
                HTTP_STATUS=status.HTTP_201_CREATED
                )
        return BaseResponse.response(status=False, message='Account is suspended!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)


class VerifyAccountUser(generics.GenericAPIView):
    def post(self, request, user_id):
        code = request.data.get('code')
        user_code = db.otp_codes.find_one({'user_id': user_id})
        
        if not user_code:
            return Response({'status': 'failed', 'error': 'code has expired'}, status=status.HTTP_400_BAD_REQUEST)
        if  code != user_code['code']:
            return Response({'status': 'failed', 'error': 'code is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            db.account_user.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_verified': True}})
            return BaseResponse.response(status=True, message='Code is verified', HTTP_STATUS=status.HTTP_200_OK)
        
class GenerateOTPCode(generics.GenericAPIView):
    def get(self, request, user_id, no_otp):
        user_data = db.account_user.find_one({'_id': user_id})
        code = Util.generate_number(int(no_otp))
        expire_at = datetime.utcnow() + timedelta(seconds=120)
        db.otp_codes.insert_one({'user_id': user_data['_id'], 'code': code, 'expireAt': expire_at})
        data = {
            'subject': 'Verification code',
            'to': user_data['email'],
            'body': f'Use this otp to verify your account {code}'
        }
        Util.email_send(data)
        return BaseResponse.response(status=True, message='otp has been sent to your email', HTTP_STATUS=status.HTTP_200_OK)


class PasswordResetView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordResetSerializer
    def patch(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            account_user = db.account_user.find_one({'_id': user['_id']})
            if serializer.validated_data['old_password'] != account_user['password']:
                return BaseResponse.response(status=False, message='Password is not correct!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)

            if serializer.validated_data['new_password'] != serializer.validated_data['confirm_password']:
                return BaseResponse.response(status=False, message='Passwords mismatch!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
            
            db.account_user.update_one({'_id': user['_id']}, {'$set': {'password': serializer.validated_data['new_password']}})
            return BaseResponse.response(status=True, message='Password changed successfully', HTTP_STATUS=status.HTTP_200_OK)
        return BaseResponse.response(status=False, message=serializer.errors, HTTP_STATUS=status.HTTP_400_BAD_REQUEST)
        
    

class SuspendAccountUser(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, acc_id):
        account_user = db.account_user.find_one({'_id': acc_id})
        if account_user['is_suspended'] == True:
            update = {'$set': {'is_suspended': False, 'status': 'Active'}}
            db.account_user.update_one({'_id': acc_id}, update)
            return BaseResponse.response(status=True, message='Account is active', HTTP_STATUS=status.HTTP_200_OK)

        update = {'$set': {'is_suspended': True, 'status': 'Suspended'}}
        db.account_user.update_one({'_id': acc_id}, update)
        return BaseResponse.response(status=True, message='Account is suspended', HTTP_STATUS=status.HTTP_200_OK)
        

class ApproveAccountUser(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, acc_id):
        update = {'$set': {'is_approved': True}}
        db.account_user.update_one({'_id': acc_id}, update)
        return BaseResponse.response(status=True, message='Account is approved', HTTP_STATUS=status.HTTP_200_OK)
    

class TransferBlockView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, acc_id):
        account_user = db.account_user.find_one({'_id': acc_id})
        if account_user['is_transfer_blocked'] == True:
            update = {'$set': {'is_transfer_blocked': False}}
            db.account_user.update_one({'_id': acc_id}, update)
            return BaseResponse.response(status=True, message='Transfers has been blocled for this user', HTTP_STATUS=status.HTTP_200_OK)

        update = {'$set': {'is_transfer_blocked': True}}
        db.account_user.update_one({'_id': acc_id}, update)
        return BaseResponse.response(status=True, message='This user can now transfer', HTTP_STATUS=status.HTTP_200_OK)
    

class TwoFactorAuthentication(generics.GenericAPIView):
    permission_classes= [IsAuthenticated]
    def post(self, request, acc_id):
        account_user = db.account_user.find_one({'_id': ObjectId(acc_id)})
        if account_user['is_two_factor'] == False:
            update = {'$set': {'is_two_factor': True}}
            db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
            return BaseResponse.response(status=True, message='two factor enabled', HTTP_STATUS=status.HTTP_200_OK)
        
        update = {'$set': {'is_two_factor': False}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
        return BaseResponse.response(status=True, message='two factor disbaled', HTTP_STATUS=status.HTTP_200_OK)
        

    

    
    
            


        


            

        


