def calculate_total(items):
    total = 0
    for item in items:
        total += item.get('price', 0) * item.get('quantity', 1)
    return total

def apply_discount(total, discount_code):
    discounts = {
        'SAVE10': 0.1,
        'SAVE20': 0.2,
        'VIP': 0.15
    }
    if discount_code in discounts:
        return total * (1 - discounts[discount_code])
    return total

class Order:
    def __init__(self, items, customer_id):
        self.items = items
        self.customer_id = customer_id
        self.status = 'pending'
    
    def process(self):
        self.status = 'processing'
        total = calculate_total(self.items)
        return total
    
    def complete(self):
        self.status = 'completed'

def validate_email(email):
    return '@' in email and '.' in email

def send_notification(email, message):
    print(f"Sending to {email}: {message}")