from rest_framework import generics, status
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string

from .serializers import AccountManagerSerializer, LoginAdminSerializer, AccountUserSerializer, PasswordResetSerializer, LoginAccountUserSerializer

from .authentications import JWTAuthentication
from .permissions import IsAuthenticated
from .utils import Util as auth_util
from united_sky_trust.base_response import BaseResponse

from bson import ObjectId
from cloudinary.uploader import upload
from datetime import datetime, timedelta
import jwt
import pymongo

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from twilio.rest import Client

db = settings.DB
            
class Transactions:
    @staticmethod
    def get_all_transactions():
        return list(db.transactions.find({}, {'_id': 0}))
    
class AccountManager:
    @staticmethod
    def get_account_manager():
        return db.account_user.find_one({'isAdmin': True})
    
@extend_schema(
    request=AccountManagerSerializer,
    responses={201: AccountManagerSerializer, 400:''}
)
class RegisterAccountManager(generics.GenericAPIView):
    serializer_class = AccountManagerSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
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
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            data = {
                '_id': payload['id'],
                'isAdmin': payload['isAdmin']
            }
            return BaseResponse.response(status=True, message='token is valid', data=data, HTTP_STATUS=status.HTTP_200_OK)
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
                'last_name': user['last_name'],
                'role': user['role'],
                'createdAt': user['createdAt']
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
    def post(self, request):
        data = request.data
        user = request.user
        if isinstance(user, AnonymousUser):
            isAnonymous = True
            user = AccountManager.get_account_manager()

        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            first_name = serializer.validated_data['first_name']
            account_user_email = db.account_user.find_one({'email': email})
            serializer.validated_data['account_manager_id'] = user['_id']

            if account_user_email and account_user_email['isVerified'] == False and isAnonymous == True:
                code = auth_util.generate_number(6)
                db.otp_codes.create_index('expireAt', expireAfterSeconds=1800)
                expire_at = datetime.utcnow() + timedelta(minutes=30)
                db.otp_codes.insert_one({'code': code, 'expireAt': expire_at, 'email': email})

                context = {
                    'customer_name': account_user_email['first_name'],
                    'otp': code
                }

                data = {
                    'subject': 'Email Confirmation',
                    'to': email,
                    'body': 'Use this otp to verify your account',
                    'html_template': render_to_string('otp.html', context=context)
                }

                auth_util.email_send(data)
                return BaseResponse.response(status=True, message='Account already exists, OTP has been sent to your email', HTTP_STATUS=status.HTTP_201_CREATED)
            user_data = serializer.save()

            if isAnonymous == True:
                # Email Functionality
                code = auth_util.generate_number(6)
                db.otp_codes.create_index('expireAt', expireAfterSeconds=1800)
                expire_at = datetime.utcnow() + timedelta(minutes=30)
                db.otp_codes.insert_one({'user_id': user_data.inserted_id, 'code': code, 'expireAt': expire_at, 'email': email})

                context = {
                    'customer_name': first_name,
                    'otp': code
                }

                data = {
                    'subject': 'Email Confirmation',
                    'to': email,
                    'body': f'Use this otp to verify your account {code}',
                    'html_template': render_to_string('otp.html', context=context)
                }
                auth_util.email_send(data)

            return BaseResponse.response(status=True, message='account created successfully', HTTP_STATUS=status.HTTP_201_CREATED)

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
        
        if account_user['isSuspended'] == False:

            # if account_user['is_two_factor'] == True:
            #     two_factor_code = Util.generate_number(4)
            #     expire_at = datetime.utcnow() + timedelta(seconds=120)
            #     db.otp_codes.insert_one({'user_id': account_user['_id'], 'code': two_factor_code, 'expireAt': expire_at})
            #     data = {
            #         'subject': 'Two Factor Authentication',
            #         'to': account_user['email'],
            #         'body': f'Use this otp to verify your login {two_factor_code}'
            #     }
            #     Util.email_send(data)
            #     return BaseResponse.response(status=True, message='check your email for 2fa code', HTTP_STATUS=status.HTTP_201_CREATED)

            token = JWTAuthentication.create_jwt(account_user)

            data={
                'token': token,
                'user_data': {
                    'email': account_user['email'],
                    'first_name': account_user['first_name'],
                    'middle_name': account_user['middle_name'],
                    'last_name': account_user['last_name'],
                    'role': account_user['role'],
                    'createdAt': account_user['createdAt']
                }}
          
            return BaseResponse.response(
                status=True,
                data=data,
                message='Login Successful!',
                HTTP_STATUS=status.HTTP_201_CREATED
                )
        return BaseResponse.response(status=False, message='Account is suspended!', HTTP_STATUS=status.HTTP_400_BAD_REQUEST)


class VerifyAccountUser(generics.GenericAPIView):
    def patch(self, request):
        otp_code = request.data.get('otp_code')
        email = request.data.get('email')
        user_code = db.otp_codes.find_one({'email': email})
        
        if not user_code:
            return Response({'status': 'failed', 'message': 'Code has expired!'}, status=status.HTTP_400_BAD_REQUEST)
        if  otp_code != user_code['code']:
            return Response({'status': 'failed', 'message': 'Code is incorrect!'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            updated_user = db.account_user.find_one_and_update({'email': email}, {'$set': {'isVerified': True}}, return_document=pymongo.ReturnDocument.AFTER)
            context = {
                    'customer_name': updated_user['first_name'],
                }

            data = {
                'subject': 'Complete KYC',
                'to': email,
                'body': f'Complete your kyc application!',
                'html_template': render_to_string('kyc.html', context=context)
            }
            auth_util.email_send(data)
            return BaseResponse.response(status=True, message='Code is verified', HTTP_STATUS=status.HTTP_200_OK)
        
class GenerateOTPCode(generics.GenericAPIView):
    def get(self, request, user_id):
        user_data = db.account_user.find_one({'_id': ObjectId(user_id)})
        code = auth_util.generate_number(6)
        expire_at = datetime.utcnow() + timedelta(minutes=5)
        db.otp_codes.insert_one({'user_id': user_data['_id'], 'code': code, 'expireAt': expire_at})
        data = {
            'subject': 'Verification code',
            'to': user_data['email'],
            'body': f'Use this otp to verify your account {code}'
        }
        auth_util.email_send(data)
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
        account_user = db.account_user.find_one({'_id': ObjectId(acc_id)})
        if account_user['isSuspended'] == True:
            update = {'$set': {'isSuspended': False,}}
            db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
            return BaseResponse.response(status=True, message='Account is active', HTTP_STATUS=status.HTTP_200_OK)

        update = {'$set': {'isSuspended': True}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
        return BaseResponse.response(status=True, message='Account is suspended', HTTP_STATUS=status.HTTP_200_OK)
        

class ApproveAccountUser(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, acc_id):
        update = {'$set': {'is_approved': True}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
        return BaseResponse.response(status=True, message='Account is approved', HTTP_STATUS=status.HTTP_200_OK)
    

class TransferBlockView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, acc_id):
        account_user = db.account_user.find_one({'_id': ObjectId(acc_id)})
        if account_user['isTransferBlocked'] == True:
            update = {'$set': {'isTransferBlocked': False}}
            db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
            return BaseResponse.response(status=True, message='Transfers has been blocked for this user', HTTP_STATUS=status.HTTP_200_OK)

        update = {'$set': {'isTransferBlocked': True}}
        db.account_user.update_one({'_id': ObjectId(acc_id)}, update)
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
    
# class TwilioTest(generics.GenericAPIView):
#     def post(self, request):
#         message_to_broadcast = ("Verify your phone number!")
#         client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
#         for recipient in settings.SMS_BROADCAST_TO_NUMBERS:
#             if recipient:
#                 client.messages.create(to=recipient,
#                                     from_='+2349016010761',
#                                     body=message_to_broadcast)
                
#         return BaseResponse.response(status=True, message='Message sent successfully', HTTP_STATUS=status.HTTP_200_OK)