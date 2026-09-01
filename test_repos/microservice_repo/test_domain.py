import pytest
from domain import Product, OrderItem, Order, InMemoryProductRepository, OrderService, InventoryService


class TestProductRepository:
    def setup_method(self):
        self.repo = InMemoryProductRepository()
        self.repo.add(Product("P1", "Widget", 10.0, 100))
        self.repo.add(Product("P2", "Gadget", 20.0, 50))
    
    def test_get_existing(self):
        product = self.repo.get("P1")
        assert product is not None
        assert product.name == "Widget"
    
    def test_get_nonexistent(self):
        assert self.repo.get("P999") is None
    
    def test_update_stock(self):
        assert self.repo.update_stock("P1", 5)
        assert self.repo.get("P1").stock == 95
    
    def test_update_stock_nonexistent(self):
        assert not self.repo.update_stock("P999", 5)


class TestOrderService:
    def setup_method(self):
        self.repo = InMemoryProductRepository()
        self.repo.add(Product("P1", "Widget", 10.0, 100))
        self.service = OrderService(self.repo)
    
    def test_create_order_success(self):
        order = self.service.create_order("C1", [OrderItem("P1", 2)])
        assert order.id.startswith("ORD-")
        assert order.status == "pending"
        assert self.repo.get("P1").stock == 98
    
    def test_create_order_insufficient_stock(self):
        with pytest.raises(ValueError, match="Insufficient stock"):
            self.service.create_order("C1", [OrderItem("P1", 150)])
    
    def test_create_order_product_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            self.service.create_order("C1", [OrderItem("P999", 1)])
    
    def test_get_order(self):
        order = self.service.create_order("C1", [OrderItem("P1", 1)])
        retrieved = self.service.get_order(order.id)
        assert retrieved is not None
        assert retrieved.id == order.id


class TestInventoryService:
    def setup_method(self):
        self.repo = InMemoryProductRepository()
        self.repo.add(Product("P1", "Widget", 10.0, 10))
        self.service = InventoryService(self.repo)
    
    def test_check_availability(self):
        assert self.service.check_availability("P1", 5)
        assert not self.service.check_availability("P1", 15)
    
    def test_restock(self):
        assert self.service.restock("P1", 20)
        assert self.repo.get("P1").stock == 30