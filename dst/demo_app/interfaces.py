from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class TimeProvider(ABC):
    """Abstract time provider for deterministic timestamps"""
    
    @abstractmethod
    def now(self) -> datetime:
        pass

class DeterministicTimeProvider(TimeProvider):
    """Controllable time provider for testing"""
    
    def __init__(self, start_time: datetime):
        self._current_time = start_time
    
    def now(self) -> datetime:
        return self._current_time
    
    def advance(self, seconds: int):
        """Advance time by specified seconds"""
        from datetime import timedelta
        self._current_time += timedelta(seconds=seconds)

class MessageQueueInterface(ABC):
    """Abstract message queue for dependency injection"""
    
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]):
        pass
    
    @abstractmethod
    async def subscribe(self, topic: str, handler):
        pass

class DeterministicMessageQueue(MessageQueueInterface):
    """Deterministic message queue for simulation testing"""
    
    def __init__(self, simulation_engine):
        self.simulation_engine = simulation_engine
        self.subscribers = {}
        self.message_id = 0
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """Schedule message delivery deterministically"""
        self.message_id += 1
        
        # Schedule message delivery with deterministic delay
        self.simulation_engine.schedule_event(
            delay=1,  # 1 simulation time unit
            event_type="message_delivery",
            data={
                "topic": topic,
                "message": message,
                "message_id": self.message_id
            }
        )
    
    async def subscribe(self, topic: str, handler):
        """Register message handler"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(handler)
    
    async def deliver_message(self, topic: str, message: Dict[str, Any]):
        """Deliver message to subscribers (called by simulation engine)"""
        if topic in self.subscribers:
            for handler in self.subscribers[topic]:
                await handler(message)

class DatabaseInterface(ABC):
    """Abstract database interface"""
    
    @abstractmethod
    def get_session(self):
        pass
    
    @abstractmethod
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_order_status(self, order_id: int, status: str):
        pass
    
    @abstractmethod
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_product_stock(self, product_id: int, new_stock: int):
        pass
    
    @abstractmethod
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_all_orders(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_all_products(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def clear_all_data(self):
        pass

class InMemoryDatabase(DatabaseInterface):
    """In-memory database for deterministic testing"""
    
    def __init__(self):
        self.orders = {}
        self.products = {}
        self.next_order_id = 1
        self.next_product_id = 1
    
    def get_session(self):
        return self  # Return self as session for simplicity
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        order_id = self.next_order_id
        self.next_order_id += 1
        
        order = {
            "id": order_id,
            "customer_id": order_data["customer_id"],
            "product_id": order_data["product_id"],
            "quantity": order_data["quantity"],
            "total_amount": order_data["total_amount"],
            "status": order_data["status"],
            "created_at": order_data["created_at"]
        }
        
        self.orders[order_id] = order
        return order
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        return self.orders.get(order_id)
    
    def update_order_status(self, order_id: int, status: str):
        if order_id in self.orders:
            self.orders[order_id]["status"] = status
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        return self.products.get(product_id)
    
    def update_product_stock(self, product_id: int, new_stock: int):
        if product_id in self.products:
            self.products[product_id]["stock_quantity"] = new_stock
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        product_id = self.next_product_id
        self.next_product_id += 1
        
        product = {
            "id": product_id,
            "name": product_data["name"],
            "price": product_data["price"],
            "stock_quantity": product_data["stock_quantity"]
        }
        
        self.products[product_id] = product
        return product
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        return list(self.orders.values())
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        return list(self.products.values())
    
    def clear_all_data(self):
        self.orders.clear()
        self.products.clear()
        self.next_order_id = 1
        self.next_product_id = 1

class SimulationEngine:
    """Central simulation engine for deterministic event scheduling"""
    
    def __init__(self):
        self.current_time = 0
        self.event_queue = []
        self.services = {}
        self.event_counter = 0  # Add counter for tie-breaking
    
    def schedule_event(self, delay: int, event_type: str, data: Dict[str, Any]):
        """Schedule an event to occur after specified delay"""
        import heapq
        
        event_time = self.current_time + delay
        # Add event_counter for deterministic ordering when times are equal
        # Format: (time, counter, event_type, data)
        event = (event_time, self.event_counter, event_type, data)
        self.event_counter += 1
        heapq.heappush(self.event_queue, event)
    
    def register_service(self, name: str, service):
        """Register a service with the simulation engine"""
        self.services[name] = service
    
    async def run_simulation(self, max_time: int = 100):
        """Run the simulation until max_time or no more events"""
        import heapq
        
        while self.event_queue and self.current_time < max_time:
            event_time, event_counter, event_type, data = heapq.heappop(self.event_queue)
            self.current_time = event_time
            
            print(f"[Time {self.current_time}] Processing {event_type}: {data}")
            
            # Handle different event types
            if event_type == "message_delivery":
                await self._handle_message_delivery(data)
            elif event_type == "http_request":
                await self._handle_http_request(data)
    
    async def _handle_message_delivery(self, data: Dict[str, Any]):
        """Handle message delivery events"""
        topic = data["topic"]
        message = data["message"]
        
        # Find the message queue and deliver the message
        for service in self.services.values():
            if hasattr(service, 'message_queue'):
                await service.message_queue.deliver_message(topic, message)
    
    async def _handle_http_request(self, data: Dict[str, Any]):
        """Handle HTTP request events"""
        service_name = data["service"]
        endpoint = data["endpoint"]
        request_data = data["request_data"]
        
        # Route to appropriate service
        if service_name in self.services:
            service = self.services[service_name]
            # Call the appropriate endpoint method
            # This would need to be implemented based on your specific endpoints