import asyncio
import aiohttp
import json
from concurrent.futures import ThreadPoolExecutor
import time

class SimulationTester:
    def __init__(self):
        self.order_service_url = "http://localhost:8001"
        self.inventory_service_url = "http://localhost:8002"
    
    async def setup_test_data(self):
        """Setup initial test products"""
        async with aiohttp.ClientSession() as session:
            # Create test products
            products = [
                {"name": "Widget A", "price": 10.0, "stock_quantity": 5},
                {"name": "Widget B", "price": 20.0, "stock_quantity": 2},
                {"name": "Widget C", "price": 30.0, "stock_quantity": 10}
            ]
            
            for product in products:
                async with session.post(
                    f"{self.inventory_service_url}/products",
                    json=product
                ) as resp:
                    result = await resp.json()
                    print(f"Created product: {result}")
    
    async def create_order(self, session, customer_id, product_id, quantity):
        """Create a single order"""
        order_data = {
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity
        }
        
        start_time = time.time()
        async with session.post(
            f"{self.order_service_url}/orders",
            json=order_data
        ) as resp:
            result = await resp.json()
            end_time = time.time()
            
            print(f"Order created: {result['id']} for customer {customer_id} "
                  f"(took {end_time - start_time:.3f}s)")
            return result
    
    async def test_race_condition(self):
        """Test multiple customers ordering the same limited stock item"""
        print("\n=== Testing Race Condition ===")
        
        # Create concurrent orders for limited stock item (product_id=2, only 2 in stock)
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(5):  # 5 customers trying to order 1 item each
                task = self.create_order(session, f"customer_{i}", 2, 1)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait a bit for async processing
            await asyncio.sleep(2)
            
            # Check final order statuses
            for result in results:
                if isinstance(result, dict) and 'id' in result:
                    await self.check_order_status(session, result['id'])
    
    async def check_order_status(self, session, order_id):
        """Check the final status of an order"""
        async with session.get(f"{self.order_service_url}/orders/{order_id}") as resp:
            order = await resp.json()
            print(f"Order {order_id}: {order['status']}")
    
    async def run_simulation(self):
        """Run the full simulation test"""
        print("Setting up test data...")
        await self.setup_test_data()
        
        print("Waiting for services to be ready...")
        await asyncio.sleep(2)
        
        await self.test_race_condition()

if __name__ == "__main__":
    # Run simulation
    tester = SimulationTester()
    asyncio.run(tester.run_simulation())