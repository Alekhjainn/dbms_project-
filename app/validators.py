import re
from datetime import datetime

def validate_isbn(isbn):
    # Basic check for ISBN format, e.g., 978-0-123-1234-1
    return bool(re.match(r'^(978|979)-\d{1,5}-\d{1,7}-\d{1,7}-\d$', isbn))

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

def validate_phone(phone):
    return bool(re.match(r'^[\d\-\+\s]{7,20}$', phone))

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_non_empty(val):
    return bool(val and str(val).strip())

def validate_numeric(val, min_val=0):
    try:
        v = float(val)
        return v >= min_val
    except (ValueError, TypeError):
        return False
