from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from interfaces import (
    TimeProvider, MessageQueueInterface, DatabaseInterface, 
    DeterministicTimeProvider, DeterministicMessageQueue, InMemoryDatabase
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
        
        @self.app.post("/orders", response_model=OrderResponse)
        async def create_order(order_req: OrderRequest):
            return await self.create_order(order_req)
        
        @self.app.get("/orders/{order_id}")
        async def get_order(order_id: int):
            return await self.get_order(order_id)
    
    async def startup(self):
        """Initialize the service"""
        print("Deterministic Order service starting up...")
        # Subscribe to inventory responses
        await self.message_queue.subscribe("inventory_checked", self.handle_inventory_response)
        print("Deterministic Order service startup complete!")
    
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
    
    async def handle_inventory_response(self, message: dict):
        """Handle inventory check responses"""
        order_id = message.get("order_id")
        available = message.get("available", False)
        
        print(f"Handling inventory response for order {order_id}: available={available}")
        
        # Update order status based on inventory check
        new_status = "confirmed" if available else "rejected"
        self.database.update_order_status(order_id, new_status)
        
        print(f"Order {order_id} status updated to: {new_status}")

# Factory functions for different configurations
def create_production_order_service():
    """Create order service with production dependencies"""
    from datetime import datetime
    from shared.models import get_db
    from shared.message_queue import MessageQueue
    
    class ProductionTimeProvider(TimeProvider):
        def now(self):
            return datetime.now()
    
    # This would use your existing database and message queue
    # database = ProductionDatabase(get_db)
    # message_queue = MessageQueue()
    # time_provider = ProductionTimeProvider()
    
    # return DeterministicOrderService(database, message_queue, time_provider)
    pass

def create_simulation_order_service(
    simulation_engine,
    database: Optional[DatabaseInterface] = None,
    start_time: Optional[str] = None
):
    """Create order service for simulation testing"""
    from datetime import datetime
    
    if database is None:
        database = InMemoryDatabase()
    
    message_queue = DeterministicMessageQueue(simulation_engine)
    
    if start_time:
        time_provider = DeterministicTimeProvider(datetime.fromisoformat(start_time))
    else:
        time_provider = DeterministicTimeProvider(datetime(2024, 1, 1, 12, 0, 0))
    
    service = DeterministicOrderService(database, message_queue, time_provider)
    service.simulation_engine = simulation_engine
    
    return service