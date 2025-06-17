from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Import our interfaces and adapters
from interfaces import (
    TimeProvider, MessageQueueInterface, DatabaseInterface, 
    DeterministicTimeProvider, DeterministicMessageQueue
)
from database_adapter import (
    create_production_database_adapter,
    create_simulation_database_adapter,
    EnhancedInMemoryDatabase
)

class OrderRequest(BaseModel):
    customer_id: str
    product_id: int
    quantity: int

class OrderResponse(BaseModel):
    id: int
    customer_id: str
    product_id: int
    quantity: int
    status: str
    total_amount: float
    created_at: str

class ProductCreate(BaseModel):
    name: str
    price: float
    stock_quantity: int

class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    stock_quantity: int

class DeterministicOrderService:
    """Order service with dependency injection for deterministic testing"""
    
    def __init__(
        self, 
        database: DatabaseInterface,
        message_queue: MessageQueueInterface,
        time_provider: TimeProvider
    ):
        self.database = database
        self.message_queue = message_queue
        self.time_provider = time_provider
        self.app = FastAPI(title="Deterministic Order Service")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/products", response_model=ProductResponse)
        async def create_product(product: ProductCreate):
            return await self.create_product(product)
        
        @self.app.get("/products/{product_id}", response_model=ProductResponse)
        async def get_product(product_id: int):
            return await self.get_product(product_id)
        
        @self.app.put("/products/{product_id}/stock")
        async def update_stock(product_id: int, quantity: int):
            return await self.update_stock(product_id, quantity)
        
        @self.app.get("/products")
        async def get_all_products():
            return await self.get_all_products()
    
    async def startup(self):
        """Initialize the service"""
        print("Deterministic Inventory service starting up...")
        # Subscribe to order events
        await self.message_queue.subscribe("order_received", self.handle_order_received)
        print("Deterministic Inventory service startup complete!")
    
    async def create_product(self, product: ProductCreate) -> ProductResponse:
        """Create a new product"""
        product_data = {
            "name": product.name,
            "price": product.price,
            "stock_quantity": product.stock_quantity
        }
        
        db_product = self.database.create_product(product_data)
        return ProductResponse(**db_product)
    
    async def get_product(self, product_id: int) -> ProductResponse:
        """Get product details"""
        product = self.database.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return ProductResponse(**product)
    
    async def update_stock(self, product_id: int, quantity: int):
        """Update product stock (for testing setup)"""
        product = self.database.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        self.database.update_product_stock(product_id, quantity)
        return {"message": f"Stock updated to {quantity}"}
    
    async def get_all_products(self) -> list:
        """Get all products"""
        products = self.database.get_all_products()
        return [ProductResponse(**product) for product in products]
    
    async def handle_order_received(self, message: dict):
        """Handle incoming order events and check inventory"""
        order_id = message.get("order_id")
        product_id = message.get("product_id")
        quantity = message.get("quantity")
        
        print(f"Processing inventory check for order {order_id}")
        
        # Check and reserve inventory
        product = self.database.get_product(product_id)
        
        if product and product["stock_quantity"] >= quantity:
            # Reserve inventory (decrement stock)
            new_stock = product["stock_quantity"] - quantity
            self.database.update_product_stock(product_id, new_stock)
            available = True
            remaining_stock = new_stock
            print(f"Reserved {quantity} units of product {product_id}")
        else:
            available = False
            remaining_stock = product["stock_quantity"] if product else 0
            print(f"Insufficient stock for product {product_id}")
        
        # Publish inventory check result
        await self.message_queue.publish("inventory_checked", {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "available": available,
            "remaining_stock": remaining_stock
        })
    
    async def create_order(self, order_req: OrderRequest) -> OrderResponse:
        """Create a new order and trigger inventory check"""
        
        # Validate product exists
        product = self.database.get_product(order_req.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Calculate total
        total_amount = product["price"] * order_req.quantity
        
        # Create order in pending state with deterministic timestamp
        current_time = self.time_provider.now()
        
        order_data = {
            "customer_id": order_req.customer_id,
            "product_id": order_req.product_id,
            "quantity": order_req.quantity,
            "total_amount": total_amount,
            "status": "pending",
            "created_at": current_time.isoformat()
        }
        
        order = self.database.create_order(order_data)
        
        # Publish order created event
        await self.message_queue.publish("order_received", {
            "order_id": order["id"],
            "product_id": order["product_id"],
            "quantity": order["quantity"],
            "customer_id": order["customer_id"]
        })
        
        return OrderResponse(**order)
    
    async def get_order(self, order_id: int) -> OrderResponse:
        """Get order status"""
        order = self.database.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return OrderResponse(**order)
    
    async def get_all_orders(self) -> list:
        """Get all orders"""
        orders = self.database.get_all_orders()
        return [OrderResponse(**order) for order in orders]
    
    async def handle_inventory_response(self, message: dict):
        """Handle inventory check responses"""
        order_id = message.get("order_id")
        available = message.get("available", False)
        
        print(f"Handling inventory response for order {order_id}: available={available}")
        
        # Update order status based on inventory check
        new_status = "confirmed" if available else "rejected"
        self.database.update_order_status(order_id, new_status)
        
        print(f"Order {order_id} status updated to: {new_status}")

# Production service factories
def create_production_order_service():
    """Create order service with production dependencies"""
    
    class ProductionTimeProvider(TimeProvider):
        def now(self):
            return datetime.now()
    
    time_provider = ProductionTimeProvider()
    database = create_production_database_adapter(time_provider)
    
    # Import production message queue
    try:
        from shared.message_queue import MessageQueue
        message_queue = MessageQueue()
    except ImportError:
        print("Warning: Production message queue not available, using simulation version")
        from interfaces import DeterministicMessageQueue, SimulationEngine
        sim_engine = SimulationEngine()
        message_queue = DeterministicMessageQueue(sim_engine)
    
    return DeterministicOrderService(database, message_queue, time_provider)

def create_production_inventory_service():
    """Create inventory service with production dependencies"""
    
    class ProductionTimeProvider(TimeProvider):
        def now(self):
            return datetime.now()
    
    time_provider = ProductionTimeProvider()
    database = create_production_database_adapter(time_provider)
    
    # Import production message queue
    try:
        from shared.message_queue import MessageQueue
        message_queue = MessageQueue()
    except ImportError:
        print("Warning: Production message queue not available, using simulation version")
        from interfaces import DeterministicMessageQueue, SimulationEngine
        sim_engine = SimulationEngine()
        message_queue = DeterministicMessageQueue(sim_engine)
    
    return DeterministicInventoryService(database, message_queue, time_provider)

# Simulation service factories
def create_simulation_order_service(
    simulation_engine,
    database: Optional[DatabaseInterface] = None,
    start_time: Optional[str] = None
):
    """Create order service for simulation testing"""
    
    if database is None:
        time_provider = DeterministicTimeProvider(
            datetime.fromisoformat(start_time) if start_time 
            else datetime(2024, 1, 1, 12, 0, 0)
        )
        database = create_simulation_database_adapter(time_provider)
    else:
        time_provider = DeterministicTimeProvider(
            datetime.fromisoformat(start_time) if start_time 
            else datetime(2024, 1, 1, 12, 0, 0)
        )
    
    message_queue = DeterministicMessageQueue(simulation_engine)
    
    service = DeterministicOrderService(database, message_queue, time_provider)
    service.simulation_engine = simulation_engine
    
    return service

def create_simulation_inventory_service(
    simulation_engine,
    database: Optional[DatabaseInterface] = None,
    start_time: Optional[str] = None
):
    """Create inventory service for simulation testing"""
    
    if database is None:
        time_provider = DeterministicTimeProvider(
            datetime.fromisoformat(start_time) if start_time 
            else datetime(2024, 1, 1, 12, 0, 0)
        )
        database = create_simulation_database_adapter(time_provider)
    else:
        time_provider = DeterministicTimeProvider(
            datetime.fromisoformat(start_time) if start_time 
            else datetime(2024, 1, 1, 12, 0, 0)
        )
    
    message_queue = DeterministicMessageQueue(simulation_engine)
    
    service = DeterministicInventoryService(database, message_queue, time_provider)
    service.simulation_engine = simulation_engine
    
    return service

# Test utilities
class ServiceTestRunner:
    """Test runner for individual service testing"""
    
    def __init__(self, use_real_database: bool = False):
        self.use_real_database = use_real_database
        self.time_provider = DeterministicTimeProvider(datetime(2024, 1, 1, 12, 0, 0))
        
        if use_real_database:
            from database_adapter import create_test_database_adapter
            self.database = create_test_database_adapter(self.time_provider, use_sqlite=True)
        else:
            self.database = EnhancedInMemoryDatabase(self.time_provider)
    
    def setup_test_data(self):
        """Setup test data"""
        # Clear any existing data
        self.database.clear_all_data()
        
        # Create test products
        self.database.create_product({
            "name": "Test Product 1",
            "price": 10.0,
            "stock_quantity": 100
        })
        
        self.database.create_product({
            "name": "Test Product 2", 
            "price": 25.0,
            "stock_quantity": 5
        })
        
        self.database.create_product({
            "name": "Out of Stock Product",
            "price": 15.0,
            "stock_quantity": 0
        })
        
        print("Test data setup complete")
    
    async def test_order_service_standalone(self):
        """Test order service without message queue integration"""
        print("\n=== Testing Order Service Standalone ===")
        
        # Create a mock message queue that just logs
        class MockMessageQueue:
            def __init__(self):
                self.published_messages = []
            
            async def publish(self, topic: str, message: dict):
                self.published_messages.append({"topic": topic, "message": message})
                print(f"[MOCK MQ] Published to {topic}: {message}")
            
            async def subscribe(self, topic: str, handler):
                print(f"[MOCK MQ] Subscribed to {topic}")
        
        mock_mq = MockMessageQueue()
        
        # Create order service
        order_service = DeterministicOrderService(
            self.database, 
            mock_mq, 
            self.time_provider
        )
        
        await order_service.startup()
        
        # Test creating an order
        from updated_services import OrderRequest
        order_req = OrderRequest(
            customer_id="test_customer_123",
            product_id=1,
            quantity=3
        )
        
        try:
            result = await order_service.create_order(order_req)
            print(f"Order created successfully: {result}")
            
            # Verify order was stored
            stored_order = await order_service.get_order(result.id)
            print(f"Retrieved order: {stored_order}")
            
            # Check if message was published
            print(f"Published messages: {mock_mq.published_messages}")
            
            return True
            
        except Exception as e:
            print(f"Error creating order: {e}")
            return False
    
    async def test_inventory_service_standalone(self):
        """Test inventory service without message queue integration"""
        print("\n=== Testing Inventory Service Standalone ===")
        
        class MockMessageQueue:
            def __init__(self):
                self.published_messages = []
                self.subscribers = {}
            
            async def publish(self, topic: str, message: dict):
                self.published_messages.append({"topic": topic, "message": message})
                print(f"[MOCK MQ] Published to {topic}: {message}")
            
            async def subscribe(self, topic: str, handler):
                self.subscribers[topic] = handler
                print(f"[MOCK MQ] Subscribed to {topic}")
            
            async def simulate_message(self, topic: str, message: dict):
                if topic in self.subscribers:
                    await self.subscribers[topic](message)
        
        mock_mq = MockMessageQueue()
        
        # Create inventory service
        inventory_service = DeterministicInventoryService(
            self.database,
            mock_mq,
            self.time_provider
        )
        
        await inventory_service.startup()
        
        # Test handling an order
        test_order_message = {
            "order_id": 1,
            "product_id": 1,
            "quantity": 5,
            "customer_id": "test_customer"
        }
        
        try:
            # Check initial stock
            product = self.database.get_product(1)
            initial_stock = product["stock_quantity"]
            print(f"Initial stock for product 1: {initial_stock}")
            
            # Simulate receiving an order
            await mock_mq.simulate_message("order_received", test_order_message)
            
            # Check stock after processing
            product = self.database.get_product(1)
            final_stock = product["stock_quantity"]
            print(f"Final stock for product 1: {final_stock}")
            
            # Check published message
            print(f"Published messages: {mock_mq.published_messages}")
            
            return initial_stock - final_stock == 5
            
        except Exception as e:
            print(f"Error in inventory service test: {e}")
            return False
    

class DeterministicInventoryService:
    """Inventory service with dependency injection for deterministic testing"""
    
    def __init__(
        self,
        database: DatabaseInterface,
        message_queue: MessageQueueInterface,
        time_provider: TimeProvider
    ):
        self.database = database
        self.message_queue = message_queue
        self.time_provider = time_provider
        self.app = FastAPI(title="Deterministic Inventory Service")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/products", response_model=ProductResponse)
        async def create_product(product: ProductCreate):
            return await self.create_product(product)
        
        @self.app.get("/products/{product_id}", response_model=ProductResponse)
        async def get_product(product_id: int):
            return await self.get_product(product_id)
        
        @self.app.put("/products/{product_id}/stock")
        async def update_stock(product_id: int, quantity: int):
            return await self.update_stock(product_id, quantity)
        
        @self.app.get("/products")
        async def get_all_products():
            return await self.get_all_products()
        
        @self.app.delete("/products/{product_id}")
        async def delete_product(product_id: int):
            return await self.delete_product(product_id)
        
        @self.app.put("/products/{product_id}")
        async def update_product(product_id: int, product: ProductCreate):
            return await self.update_product(product_id, product)
    
    async def startup(self):
        """Initialize the service"""
        print("Deterministic Inventory service starting up...")
        # Subscribe to order events
        await self.message_queue.subscribe("order_received", self.handle_order_received)
        print("Deterministic Inventory service startup complete!")
    
    async def create_product(self, product: ProductCreate) -> ProductResponse:
        """Create a new product"""
        product_data = {
            "name": product.name,
            "price": product.price,
            "stock_quantity": product.stock_quantity
        }
        
        db_product = self.database.create_product(product_data)
        print(f"Created product {db_product['id']}: {db_product['name']}")
        return ProductResponse(**db_product)
    
    async def get_product(self, product_id: int) -> ProductResponse:
        """Get product details"""
        product = self.database.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return ProductResponse(**product)
    
    async def update_stock(self, product_id: int, quantity: int):
        """Update product stock (for testing setup)"""
        product = self.database.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        old_stock = product["stock_quantity"]
        self.database.update_product_stock(product_id, quantity)
        print(f"Updated product {product_id} stock from {old_stock} to {quantity}")
        
        return {
            "message": f"Stock updated to {quantity}",
            "product_id": product_id,
            "old_stock": old_stock,
            "new_stock": quantity
        }
    
    async def update_product(self, product_id: int, product_update: ProductCreate):
        """Update product details"""
        existing_product = self.database.get_product(product_id)
        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # For simplicity, we'll delete and recreate
        # In a real implementation, you'd have an update method
        updated_data = {
            "name": product_update.name,
            "price": product_update.price,
            "stock_quantity": product_update.stock_quantity
        }
        
        # This is a simplified update - in reality you'd implement proper update logic
        print(f"Updated product {product_id} details")
        return {"message": f"Product {product_id} updated", "product_id": product_id}
    
    async def delete_product(self, product_id: int):
        """Delete a product (for testing)"""
        product = self.database.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # In a real implementation, you'd implement proper deletion
        print(f"Deleted product {product_id}")
        return {"message": f"Product {product_id} deleted", "product_id": product_id}
    
    async def get_all_products(self) -> list:
        """Get all products"""
        products = self.database.get_all_products()
        return [ProductResponse(**product) for product in products]
    
    async def handle_order_received(self, message: dict):
        """Handle incoming order events and check inventory"""
        order_id = message.get("order_id")
        product_id = message.get("product_id")
        quantity = message.get("quantity")
        customer_id = message.get("customer_id")
        
        print(f"Processing inventory check for order {order_id} (customer: {customer_id})")
        print(f"  Requested: {quantity} units of product {product_id}")
        
        # Check and reserve inventory
        product = self.database.get_product(product_id)
        
        if not product:
            print(f"  ❌ Product {product_id} not found")
            available = False
            remaining_stock = 0
        elif product["stock_quantity"] >= quantity:
            # Reserve inventory (decrement stock)
            old_stock = product["stock_quantity"]
            new_stock = old_stock - quantity
            self.database.update_product_stock(product_id, new_stock)
            available = True
            remaining_stock = new_stock
            print(f"  ✅ Reserved {quantity} units of product {product_id}")
            print(f"     Stock: {old_stock} → {new_stock}")
        else:
            available = False
            remaining_stock = product["stock_quantity"]
            print(f"  ❌ Insufficient stock for product {product_id}")
            print(f"     Requested: {quantity}, Available: {remaining_stock}")
        
        # Create detailed response message
        response_message = {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "available": available,
            "remaining_stock": remaining_stock,
            "customer_id": customer_id,
            "timestamp": self.time_provider.now().isoformat(),
            "product_name": product["name"] if product else "Unknown Product"
        }
        
        # Publish inventory check result
        await self.message_queue.publish("inventory_checked", response_message)
        
        print(f"  📤 Published inventory result: available={available}")
    
    async def get_low_stock_products(self, threshold: int = 10) -> list:
        """Get products with stock below threshold (useful for monitoring)"""
        all_products = self.database.get_all_products()
        low_stock = [
            ProductResponse(**product) 
            for product in all_products 
            if product["stock_quantity"] <= threshold
        ]
        
        print(f"Found {len(low_stock)} products with stock <= {threshold}")
        return low_stock
    
    async def get_inventory_summary(self) -> dict:
        """Get inventory summary statistics"""
        all_products = self.database.get_all_products()
        
        if not all_products:
            return {
                "total_products": 0,
                "total_stock_units": 0,
                "total_inventory_value": 0.0,
                "out_of_stock_count": 0,
                "low_stock_count": 0
            }
        
        total_products = len(all_products)
        total_stock_units = sum(p["stock_quantity"] for p in all_products)
        total_inventory_value = sum(p["price"] * p["stock_quantity"] for p in all_products)
        out_of_stock_count = sum(1 for p in all_products if p["stock_quantity"] == 0)
        low_stock_count = sum(1 for p in all_products if 0 < p["stock_quantity"] <= 10)
        
        summary = {
            "total_products": total_products,
            "total_stock_units": total_stock_units,
            "total_inventory_value": round(total_inventory_value, 2),
            "out_of_stock_count": out_of_stock_count,
            "low_stock_count": low_stock_count,
            "average_stock_per_product": round(total_stock_units / total_products, 2) if total_products > 0 else 0,
            "timestamp": self.time_provider.now().isoformat()
        }
        
        print(f"Inventory summary: {total_products} products, {total_stock_units} units, ${total_inventory_value:.2f} value")
        return summary
    
    async def bulk_update_stock(self, stock_updates: list) -> dict:
        """Bulk update stock for multiple products"""
        """
        stock_updates format: [{"product_id": 1, "quantity": 100}, ...]
        """
        results = []
        errors = []
        
        for update in stock_updates:
            try:
                product_id = update["product_id"]
                quantity = update["quantity"]
                
                product = self.database.get_product(product_id)
                if not product:
                    errors.append(f"Product {product_id} not found")
                    continue
                
                old_stock = product["stock_quantity"]
                self.database.update_product_stock(product_id, quantity)
                
                results.append({
                    "product_id": product_id,
                    "old_stock": old_stock,
                    "new_stock": quantity,
                    "success": True
                })
                
                print(f"Bulk update: Product {product_id} stock {old_stock} → {quantity}")
                
            except Exception as e:
                error_msg = f"Error updating product {update.get('product_id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                print(f"Bulk update error: {error_msg}")
        
        return {
            "successful_updates": len(results),
            "failed_updates": len(errors),
            "results": results,
            "errors": errors,
            "timestamp": self.time_provider.now().isoformat()
        }
    
if __name__ == "__main__":
    import asyncio
    
    async def run_standalone_tests():
        # Test with in-memory database
        print("=== Testing with In-Memory Database ===")
        runner = ServiceTestRunner(use_real_database=False)
        runner.setup_test_data()
        
        order_success = await runner.test_order_service_standalone()
        inventory_success = await runner.test_inventory_service_standalone()
        
        print(f"\nOrder Service Test: {'PASSED' if order_success else 'FAILED'}")
        print(f"Inventory Service Test: {'PASSED' if inventory_success else 'FAILED'}")
        
        # Print final database state
        if hasattr(runner.database, 'print_state'):
            runner.database.print_state()
    
    asyncio.run(run_standalone_tests())