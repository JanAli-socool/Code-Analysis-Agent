import pytest
from order_service import calculate_total, apply_discount, Order, validate_email


class TestCalculateTotal:
    def test_basic_calculation(self):
        items = [{'price': 10, 'quantity': 2}, {'price': 5, 'quantity': 3}]
        assert calculate_total(items) == 35
    
    def test_empty_items(self):
        assert calculate_total([]) == 0
    
    def test_missing_price(self):
        items = [{'quantity': 2}]
        assert calculate_total(items) == 0


class TestApplyDiscount:
    def test_valid_codes(self):
        assert apply_discount(100, 'SAVE10') == 90
        assert apply_discount(100, 'SAVE20') == 80
        assert apply_discount(100, 'VIP') == 85
    
    def test_invalid_code(self):
        assert apply_discount(100, 'INVALID') == 100


class TestOrder:
    def test_order_creation(self):
        order = Order([{'price': 10}], 'customer1')
        assert order.status == 'pending'
        assert order.customer_id == 'customer1'
    
    def test_order_process(self):
        order = Order([{'price': 10, 'quantity': 2}], 'customer1')
        total = order.process()
        assert total == 20
        assert order.status == 'processing'
    
    def test_order_complete(self):
        order = Order([], 'customer1')
        order.complete()
        assert order.status == 'completed'


class TestValidateEmail:
    def test_valid_emails(self):
        assert validate_email('test@example.com')
        assert validate_email('user.name@domain.org')
    
    def test_invalid_emails(self):
        assert not validate_email('invalid')
        assert not validate_email('@domain.com')
        assert not validate_email('user@')