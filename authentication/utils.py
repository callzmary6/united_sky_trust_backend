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
        to_list = []
        if isinstance(data['to'], list):
            to_list = data['to']
        else:
            to_list.append(data['to'])

        email = EmailMultiAlternatives(
            subject=data['subject'],
            body=data['body'],
            from_email="Unity Heritage Trust <{}>".format(settings.EMAIL_HOST_USER),
            to=to_list,
        )
        email.attach_alternative(data['html_template'], 'text/html')
        email.send()


    
    