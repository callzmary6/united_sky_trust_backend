import random

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

class Util:
    @staticmethod
    def generate_number(limit):
        number = ''
        for i in range(limit):
            number += (str(random.randint(0, 9)))
        return number
    
    @staticmethod
    def email_send(data):
        email = EmailMultiAlternatives(
            subject=data['subject'],
            body=data['body'],
            from_email=settings.EMAIL_HOST_USER,
            to=[data['to']],
        )
        email.attach_alternative(data['html_template'], 'text/html')
        email.send()


    
    