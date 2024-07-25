from rest_framework import generics, status
from rest_framework.response import Response

from django.conf import settings

from .serializers import AccountManagerSerializer, LoginSerializer, AccountUserSerializer, PasswordResetSerializer
from .authentications import JWTAuthentication
from .permissions import IsAuthenticated
from bson import ObjectId

db = settings.DB

class RegisterAccountManager(generics.GenericAPIView):
    def post(self, request):
        serializer = AccountManagerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': {'email': serializer.validated_data['email'], 'first_name': serializer.validated_data['first_name'], 'last_name': serializer.validated_data['last_name']}}, status=status.HTTP_201_CREATED)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class LoginAccountManager(generics.GenericAPIView):
    serializer_class = LoginSerializer
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email and password:
            return Response({'email': 'email should not be empty!', 'password': 'password should not be empty!'}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({'email': 'email should not be empty!'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'password': 'password should not be empty!'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = db.account_manager.find_one({'email': email})
        
        if not user:
            return Response({'status': 'failed', 'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)
        
        token = JWTAuthentication.create_jwt(user)

        users = db.account_user.find({'account_manager_id': str(user['_id'])})

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
    permission_classes = [IsAuthenticated,]
    def post(self, request):
        data = request.data
        user = request.user
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.validated_data['account_manager_id'] = str(user['_id'])
            user_data = serializer.save()

            # Email Functionality

            return Response({
                'status': 'success',
                'user_data': {
                    'id': str(user_data['id']),
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'account_number': user_data['account_number']
                }
            }, status=status.HTTP_201_CREATED)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

class PasswordResetView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordResetSerializer
    def post(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            account_manager = db.account_manager.find_one({'_id': user['_id']})
            if serializer.validated_data['old_password'] != account_manager['password']:
                return Response({'status': 'failed', 'error': 'Password is not correct!'}, status=status.HTTP_400_BAD_REQUEST)
            if serializer.validated_data['new_password'] != serializer.validated_data['confirm_password']:
                return Response({'status': 'failed', 'error': 'Passwords mismatch!'}, status=status.HTTP_400_BAD_REQUEST)
            
            db.account_manager.update_one({'_id': user['_id']}, {'$set': {'password': serializer.validated_data['new_password']}})
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        return Response({'status': 'failed', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

class SuspendAccountUser(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, acc_id):
        update = {'$set': {'status': 'suspended'}}
        account_user = db.account_user.find_one_and_update({'_id': ObjectId(acc_id)}, update)
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
    


    
    
            


        


            

        


