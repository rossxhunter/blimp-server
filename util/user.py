from config import db_manager
import random
import string


def generate_referral_code():
    is_code_valid = False
    while not is_code_valid:
        referral_code = new_referral_code()
        existing_codes = db_manager.query("""
        SELECT id
        FROM user
        WHERE referral_code = "{referral_code}"
        """)
        if len(existing_codes) == 0:
            is_code_valid = True
    return referral_code


def new_referral_code():
    letters = string.ascii_uppercase
    code = ''.join(random.choice(letters) for i in range(8))
    return code
