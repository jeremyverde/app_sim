import asyncio
from datetime import datetime
from interfaces import SimulationEngine, InMemoryDatabase
from deterministic_order_service import create_simulation_order_service

class DeterministicInventoryService:
    """Simplified inventory service for simulation"""
    
    def __init__(self, database, message_queue, time_provider):
        self.database = database
        self.message_queue = message_queue
        self.time_provider = time_provider
    
    async def startup(self):
        """Initialize the service"""
        print("Deterministic Inventory service starting up...")
        await self.message_queue.subscribe("order_received", self.handle_order_received)
        print("Deterministic Inventory service startup complete!")
    
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
            print(f"Reserved {quantity} units of product {product_id}")
        else:
            available = False
            print(f"Insufficient stock for product {product_id}")
        
        # Publish inventory check result
        await self.message_queue.publish("inventory_checked", {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "available": available,
            "remaining_stock": product["stock_quantity"] if product else 0
        })

class SimulationTestRunner:
    """Test runner for deterministic simulation testing"""
    
    def __init__(self):
        self.simulation_engine = SimulationEngine()
        self.database = InMemoryDatabase()
        self.test_results = []
    
    async def setup_services(self):
        """Setup all services for simulation"""
        
        # Create order service
        self.order_service = create_simulation_order_service(
            self.simulation_engine,
            self.database,
            "2024-01-01T12:00:00"
        )
        
        # Create inventory service
        self.inventory_service = DeterministicInventoryService(
            self.database,
            self.order_service.message_queue,
            self.order_service.time_provider
        )
        
        # Register services with simulation engine
        self.simulation_engine.register_service("order", self.order_service)
        self.simulation_engine.register_service("inventory", self.inventory_service)
        
        # Initialize services
        await self.order_service.startup()
        await self.inventory_service.startup()
    
    def setup_test_data(self):
        """Setup initial test data"""
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
        
        print("Test data setup complete")
    
    async def run_test_scenario(self, scenario_name: str, test_actions: list):
        """Run a specific test scenario"""
        print(f"\n=== Running Scenario: {scenario_name} ===")
        
        scenario_result = {
            "name": scenario_name,
            "actions": [],
            "final_state": {}
        }
        
        for action in test_actions:
            print(f"\n[Action] {action['type']}")
            
            if action["type"] == "create_order":
                order_req = action["data"]
                try:
                    # Simulate the order creation
                    from deterministic_order_service import OrderRequest
                    order_request = OrderRequest(**order_req)
                    result = await self.order_service.create_order(order_request)
                    
                    action_result = {
                        "type": "create_order",
                        "success": True,
                        "result": result.dict()
                    }
                    print(f"Order created: {result.id}")
                    
                except Exception as e:
                    action_result = {
                        "type": "create_order",
                        "success": False,
                        "error": str(e)
                    }
                    print(f"Order creation failed: {e}")
            
            elif action["type"] == "advance_time":
                seconds = action["seconds"]
                self.order_service.time_provider.advance(seconds)
                action_result = {
                    "type": "advance_time",
                    "seconds": seconds,
                    "new_time": self.order_service.time_provider.now().isoformat()
                }
                print(f"Time advanced by {seconds} seconds")
            
            elif action["type"] == "process_events":
                # Run simulation to process any pending events
                await self.simulation_engine.run_simulation(max_time=self.simulation_engine.current_time + 10)
                action_result = {
                    "type": "process_events",
                    "simulation_time": self.simulation_engine.current_time
                }
            
            elif action["type"] == "check_order_status":
                order_id = action["order_id"]
                try:
                    result = await self.order_service.get_order(order_id)
                    action_result = {
                        "type": "check_order_status",
                        "order_id": order_id,
                        "status": result.status,
                        "result": result.dict()
                    }
                    print(f"Order {order_id} status: {result.status}")
                except Exception as e:
                    action_result = {
                        "type": "check_order_status",
                        "order_id": order_id,
                        "error": str(e)
                    }
            
            scenario_result["actions"].append(action_result)
        
        # Capture final system state
        scenario_result["final_state"] = {
            "orders": dict(self.database.orders),
            "products": dict(self.database.products),
            "simulation_time": self.simulation_engine.current_time
        }
        
        self.test_results.append(scenario_result)
        print(f"\n=== Scenario Complete: {scenario_name} ===")
        return scenario_result

# Example test scenarios
async def run_deterministic_tests():
    """Run deterministic test scenarios"""
    
    runner = SimulationTestRunner()
    await runner.setup_services()
    runner.setup_test_data()
    
    # Test Scenario 1: Successful Order Processing
    scenario1_actions = [
        {
            "type": "create_order",
            "data": {
                "customer_id": "customer_123",
                "product_id": 1,
                "quantity": 2
            }
        },
        {
            "type": "process_events"
        },
        {
            "type": "check_order_status",
            "order_id": 1
        }
    ]
    
    result1 = await runner.run_test_scenario("Successful Order Processing", scenario1_actions)
    
    # Test Scenario 2: Insufficient Inventory
    scenario2_actions = [
        {
            "type": "create_order",
            "data": {
                "customer_id": "customer_456",
                "product_id": 2,
                "quantity": 10  # More than available stock
            }
        },
        {
            "type": "process_events"
        },
        {
            "type": "check_order_status",
            "order_id": 2
        }
    ]
    
    result2 = await runner.run_test_scenario("Insufficient Inventory", scenario2_actions)
    
    # Print final results
    print("\n" + "="*50)
    print("SIMULATION TEST RESULTS")
    print("="*50)
    
    for result in runner.test_results:
        print(f"\nScenario: {result['name']}")
        print(f"Actions: {len(result['actions'])}")
        print(f"Final Orders: {len(result['final_state']['orders'])}")
        print(f"Final Products: {len(result['final_state']['products'])}")
        
        # Show order statuses
        for order_id, order in result['final_state']['orders'].items():
            print(f"  Order {order_id}: {order['status']}")

if __name__ == "__main__":
    asyncio.run(run_deterministic_tests())
