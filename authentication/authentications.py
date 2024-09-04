import jwt
from datetime import datetime, timedelta

from django.conf import settings

from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed, ParseError

db = settings.DB

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        jwt_token = request.META.get('HTTP_AUTHORIZATION')
        if jwt_token is None:
            return None
        
        jwt_token = JWTAuthentication.get_the_token_from_header(jwt_token)

        # Decode the JWT and verify its signature

        try:
            payload = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.exceptions.InvalidSignatureError:
            raise AuthenticationFailed('Invalid signature')
        except jwt.exceptions.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid Token')
        except:
            raise ParseError()
        
        # Get user from the database
        email = payload.get('user_identifier')
        if email is None:
            AuthenticationFailed('User identifier not found in JWT')

        user = db.account_user.find_one({'email': email})
        if user is None:
            raise AuthenticationFailed('User not found')
        
        # return the user and token payload 
        # user['_id']
        return user, payload
    
    def authenticate_header(self, request):
        return 'Bearer'
    
    @classmethod
    def create_jwt(cls, user):
        # create the jwt payload 
        payload = {
            'user_identifier': user['email'],
            'exp': datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRY_TIME),
            'iat': datetime.now().timestamp(),
            'id': str(user['_id']),
            'isAdmin': user['isAdmin']
        }

        # encode the jwt token with the secret key
        jwt_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        return jwt_token
    
    @classmethod
    def get_the_token_from_header(cls, token):
        token = token.replace('Bearer', '').replace(' ', '') 
        return token 
    