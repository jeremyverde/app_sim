from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from interfaces import DatabaseInterface, TimeProvider

# Import your existing models
try:
    from models import Product, Order, Base
except ImportError:
    # If models not available, create simplified versions for testing
    print("Warning: Could not import models, using simplified versions")
    
    class Product:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class Order:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

class SQLAlchemyDatabaseAdapter(DatabaseInterface):
    """Production database adapter using SQLAlchemy"""
    
    def __init__(self, session_factory, time_provider: TimeProvider):
        self.session_factory = session_factory
        self.time_provider = time_provider
    
    def get_session(self):
        """Get a new database session"""
        return self.session_factory()
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new order in the database"""
        session = self.get_session()
        try:
            # Convert created_at string back to datetime if it's a string
            created_at = order_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif created_at is None:
                created_at = self.time_provider.now()
            
            order = Order(
                customer_id=order_data["customer_id"],
                product_id=order_data["product_id"],
                quantity=order_data["quantity"],
                total_amount=order_data["total_amount"],
                status=order_data["status"],
                created_at=created_at,
                updated_at=created_at
            )
            
            session.add(order)
            session.commit()
            session.refresh(order)
            
            # Convert to dictionary
            result = {
                "id": order.id,
                "customer_id": order.customer_id,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None
            }
            
            return result
            
        finally:
            session.close()
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        session = self.get_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            
            return {
                "id": order.id,
                "customer_id": order.customer_id,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None
            }
            
        finally:
            session.close()
    
    def update_order_status(self, order_id: int, status: str):
        """Update order status"""
        session = self.get_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = status
                order.updated_at = self.time_provider.now()
                session.commit()
                print(f"Updated order {order_id} status to {status}")
            else:
                print(f"Order {order_id} not found for status update")
                
        finally:
            session.close()
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        session = self.get_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            return {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "stock_quantity": product.stock_quantity,
                "created_at": product.created_at.isoformat() if hasattr(product, 'created_at') and product.created_at else None
            }
            
        finally:
            session.close()
    
    def update_product_stock(self, product_id: int, new_stock: int):
        """Update product stock quantity"""
        session = self.get_session()
        try:
            product = session.query(Product).filter(Product.id == product_id).first()
            if product:
                old_stock = product.stock_quantity
                product.stock_quantity = new_stock
                session.commit()
                print(f"Updated product {product_id} stock from {old_stock} to {new_stock}")
            else:
                print(f"Product {product_id} not found for stock update")
                
        finally:
            session.close()
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product"""
        session = self.get_session()
        try:
            created_at = self.time_provider.now()
            
            product = Product(
                name=product_data["name"],
                price=product_data["price"],
                stock_quantity=product_data["stock_quantity"],
                created_at=created_at
            )
            
            session.add(product)
            session.commit()
            session.refresh(product)
            
            return {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "stock_quantity": product.stock_quantity,
                "created_at": product.created_at.isoformat() if product.created_at else None
            }
            
        finally:
            session.close()
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """Get all orders (useful for testing and debugging)"""
        session = self.get_session()
        try:
            orders = session.query(Order).all()
            return [
                {
                    "id": order.id,
                    "customer_id": order.customer_id,
                    "product_id": order.product_id,
                    "quantity": order.quantity,
                    "total_amount": order.total_amount,
                    "status": order.status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "updated_at": order.updated_at.isoformat() if order.updated_at else None
                }
                for order in orders
            ]
        finally:
            session.close()
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products (useful for testing and debugging)"""
        session = self.get_session()
        try:
            products = session.query(Product).all()
            return [
                {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "stock_quantity": product.stock_quantity,
                    "created_at": product.created_at.isoformat() if hasattr(product, 'created_at') and product.created_at else None
                }
                for product in products
            ]
        finally:
            session.close()
    
    def clear_all_data(self):
        """Clear all data (useful for testing)"""
        session = self.get_session()
        try:
            session.query(Order).delete()
            session.query(Product).delete()
            session.commit()
            print("Cleared all database data")
        finally:
            session.close()

class EnhancedInMemoryDatabase(DatabaseInterface):
    """Enhanced in-memory database for deterministic testing with more realistic behavior"""
    
    def __init__(self, time_provider: TimeProvider):
        self.orders = {}
        self.products = {}
        self.next_order_id = 1
        self.next_product_id = 1
        self.time_provider = time_provider
        
        # Track operations for debugging
        self.operation_log = []
    
    def _log_operation(self, operation: str, details: Dict[str, Any]):
        """Log database operations for debugging"""
        log_entry = {
            "timestamp": self.time_provider.now().isoformat(),
            "operation": operation,
            "details": details
        }
        self.operation_log.append(log_entry)
        print(f"[DB] {operation}: {details}")
    
    def get_session(self):
        """Return self as session for compatibility"""
        return self
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new order"""
        order_id = self.next_order_id
        self.next_order_id += 1
        
        # Handle created_at timestamp
        created_at = order_data.get("created_at")
        if isinstance(created_at, str):
            # Already a string, use as-is
            pass
        elif created_at is None:
            created_at = self.time_provider.now().isoformat()
        else:
            created_at = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
        
        order = {
            "id": order_id,
            "customer_id": order_data["customer_id"],
            "product_id": order_data["product_id"],
            "quantity": order_data["quantity"],
            "total_amount": order_data["total_amount"],
            "status": order_data["status"],
            "created_at": created_at,
            "updated_at": created_at
        }
        
        self.orders[order_id] = order
        
        self._log_operation("CREATE_ORDER", {
            "order_id": order_id,
            "customer_id": order_data["customer_id"],
            "product_id": order_data["product_id"],
            "status": order_data["status"]
        })
        
        return order.copy()
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        order = self.orders.get(order_id)
        if order:
            self._log_operation("GET_ORDER", {"order_id": order_id, "found": True})
            return order.copy()
        else:
            self._log_operation("GET_ORDER", {"order_id": order_id, "found": False})
            return None
    
    def update_order_status(self, order_id: int, status: str):
        """Update order status"""
        if order_id in self.orders:
            old_status = self.orders[order_id]["status"]
            self.orders[order_id]["status"] = status
            self.orders[order_id]["updated_at"] = self.time_provider.now().isoformat()
            
            self._log_operation("UPDATE_ORDER_STATUS", {
                "order_id": order_id,
                "old_status": old_status,
                "new_status": status
            })
        else:
            self._log_operation("UPDATE_ORDER_STATUS", {
                "order_id": order_id,
                "error": "order_not_found"
            })
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        product = self.products.get(product_id)
        if product:
            self._log_operation("GET_PRODUCT", {"product_id": product_id, "found": True})
            return product.copy()
        else:
            self._log_operation("GET_PRODUCT", {"product_id": product_id, "found": False})
            return None
    
    def update_product_stock(self, product_id: int, new_stock: int):
        """Update product stock quantity"""
        if product_id in self.products:
            old_stock = self.products[product_id]["stock_quantity"]
            self.products[product_id]["stock_quantity"] = new_stock
            
            self._log_operation("UPDATE_PRODUCT_STOCK", {
                "product_id": product_id,
                "old_stock": old_stock,
                "new_stock": new_stock
            })
        else:
            self._log_operation("UPDATE_PRODUCT_STOCK", {
                "product_id": product_id,
                "error": "product_not_found"
            })
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product"""
        product_id = self.next_product_id
        self.next_product_id += 1
        
        created_at = self.time_provider.now().isoformat()
        
        product = {
            "id": product_id,
            "name": product_data["name"],
            "price": product_data["price"],
            "stock_quantity": product_data["stock_quantity"],
            "created_at": created_at
        }
        
        self.products[product_id] = product
        
        self._log_operation("CREATE_PRODUCT", {
            "product_id": product_id,
            "name": product_data["name"],
            "stock": product_data["stock_quantity"]
        })
        
        return product.copy()
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """Get all orders"""
        return [order.copy() for order in self.orders.values()]
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products"""
        return [product.copy() for product in self.products.values()]
    
    def clear_all_data(self):
        """Clear all data"""
        self.orders.clear()
        self.products.clear()
        self.next_order_id = 1
        self.next_product_id = 1
        self.operation_log.clear()
        
        self._log_operation("CLEAR_ALL_DATA", {})
    
    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get operation log for debugging"""
        return self.operation_log.copy()
    
    def print_state(self):
        """Print current database state for debugging"""
        print("\n=== Database State ===")
        print(f"Orders: {len(self.orders)}")
        for order_id, order in self.orders.items():
            print(f"  Order {order_id}: {order['status']} - Customer {order['customer_id']}")
        
        print(f"Products: {len(self.products)}")
        for product_id, product in self.products.items():
            print(f"  Product {product_id}: {product['name']} - Stock: {product['stock_quantity']}")
        
        print("======================\n")

# Factory functions for creating database adapters

def create_production_database_adapter(time_provider: TimeProvider):
    """Create production database adapter using existing models"""
    try:
        from models import SessionLocal
        return SQLAlchemyDatabaseAdapter(SessionLocal, time_provider)
    except ImportError as e:
        print(f"Error importing production models: {e}")
        print("Falling back to in-memory database")
        return EnhancedInMemoryDatabase(time_provider)

def create_test_database_adapter(time_provider: TimeProvider, use_sqlite: bool = False):
    """Create test database adapter - can use SQLite or in-memory"""
    if use_sqlite:
        # Create a test SQLite database
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Use in-memory SQLite for tests
        engine = create_engine("sqlite:///:memory:", echo=False)
        
        # Create tables
        try:
            Base.metadata.create_all(engine)
            TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            return SQLAlchemyDatabaseAdapter(TestSessionLocal, time_provider)
        except Exception as e:
            print(f"Error creating test SQLite database: {e}")
            print("Falling back to in-memory database")
            return EnhancedInMemoryDatabase(time_provider)
    else:
        return EnhancedInMemoryDatabase(time_provider)

def create_simulation_database_adapter(time_provider: TimeProvider):
    """Create simulation database adapter (always in-memory for determinism)"""
    return EnhancedInMemoryDatabase(time_provider)
