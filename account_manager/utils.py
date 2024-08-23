import random
import string
from datetime import datetime

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings

class Util:

    @staticmethod
    def generate_code():
        prefix = "HUT/"
        # Generate a random alphanumeric string of length 8
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        # Get the current month and year in MMYY format
        date_part = datetime.now().strftime("%m%y")
        # Combine all parts
        code = f"{prefix}{random_part}-{date_part}"
        return code
    
    @staticmethod
    def send_custom_mail(data):
        email = EmailMessage(
            subject= data['subject'],
            from_email = settings.EMAIL_HOST_USER,
            to = [data['to']],
            body = data['body'],
        )
        email.content_subtype = 'html'
        email.send()