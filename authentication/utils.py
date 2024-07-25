import random

class Util:
    @staticmethod
    def generate_number(limit):
        number = ''
        for i in range(limit):
            number += (str(random.randint(0, 9)))
        return number
    