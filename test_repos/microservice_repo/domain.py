from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod
import json


@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int


@dataclass
class OrderItem:
    product_id: str
    quantity: int


@dataclass
class Order:
    id: str
    items: List[OrderItem]
    customer_id: str
    status: str = "pending"


class ProductRepository(ABC):
    @abstractmethod
    def get(self, product_id: str) -> Optional[Product]:
        pass
    
    @abstractmethod
    def update_stock(self, product_id: str, quantity: int) -> bool:
        pass


class InMemoryProductRepository(ProductRepository):
    def __init__(self):
        self.products = {}
    
    def get(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)
    
    def update_stock(self, product_id: str, quantity: int) -> bool:
        if product_id in self.products:
            self.products[product_id].stock -= quantity
            return True
        return False
    
    def add(self, product: Product):
        self.products[product.id] = product


class OrderService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo
        self.orders = {}
    
    def create_order(self, customer_id: str, items: List[OrderItem]) -> Order:
        for item in items:
            product = self.product_repo.get(item.product_id)
            if not product:
                raise ValueError(f"Product {item.product_id} not found")
            if product.stock < item.quantity:
                raise ValueError(f"Insufficient stock for {product.name}")
        
        order_id = f"ORD-{len(self.orders) + 1:06d}"
        order = Order(id=order_id, items=items, customer_id=customer_id)
        
        for item in items:
            self.product_repo.update_stock(item.product_id, item.quantity)
        
        self.orders[order_id] = order
        return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)


class InventoryService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo
    
    def check_availability(self, product_id: str, quantity: int) -> bool:
        product = self.product_repo.get(product_id)
        return product is not None and product.stock >= quantity
    
    def restock(self, product_id: str, quantity: int) -> bool:
        product = self.product_repo.get(product_id)
        if product:
            product.stock += quantity
            return True
        return False