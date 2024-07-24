from rest_framework import generics, status
from rest_framework.response import Response

from django.conf import settings

from .serializers import AccountManagerSerializer, LoginSerializer
from .authentications import JWTAuthentication

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

        return Response({
            'status': 'success',
            'message': 'You have logged in successfully',
            'access_token': token,
            'user': {
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name']
        }
    })

            

        


