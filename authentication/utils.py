import random

from django.core.mail import EmailMessage
from django.conf import settings

class Util:
    @staticmethod
    def generate_number(limit):
        number = ''
        for i in range(limit):
            number += (str(random.randint(0, 9)))
        return number
    
    @staticmethod
    def email_send(data):
        email = EmailMessage(
            subject=data['subject'],
            body=data['body'],
            from_email=settings.EMAIL_HOST_USER,
            to=[data['to']],
        )
        email.send()


    
    