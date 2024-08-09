import random 
import string
import datetime

class Util:
    @staticmethod
    def generate_formatted_code(prefix='Hut', transaction_type='e-topup'):
        # Generate date part (assuming current date)
        date_part = datetime.datetime.now().strftime("%m%d")
        
        # Generate random alphanumeric string
        random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        # Combine all parts
        formatted_code = f"{prefix}-{date_part}-{transaction_type}-{random_part}"
        
        return formatted_code
    
    @staticmethod
    def generate_card_number(limit, prefix):
        number = f'{prefix}'
        for i in range(limit):
            number += (str(random.randint(0, 9)))
        return number