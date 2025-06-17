# comprehensive_simulation_test.py - Complete simulation test example

import asyncio
from datetime import datetime
from typing import List, Dict, Any

# Import all our components
from interfaces import SimulationEngine, DeterministicTimeProvider
from database_adapter import create_simulation_database_adapter
from updated_services import (
    create_simulation_order_service, 
    create_simulation_inventory_service,
    OrderRequest
)

class ComprehensiveSimulationTest:
    """Comprehensive simulation test framework"""
    
    def __init__(self, start_time: str = "2024-01-01T12:00:00"):
        self.simulation_engine = SimulationEngine()
        self.start_time = start_time
        self.time_provider = DeterministicTimeProvider(datetime.fromisoformat(start_time))
        self.database = create_simulation_database_adapter(self.time_provider)
        
        # Test results tracking
        self.test_results = []
        self.performance_metrics = {}
        
    async def setup_services(self):
        """Setup all services for comprehensive testing"""
        print("Setting up services for comprehensive simulation...")
        
        # Create services with shared database
        self.order_service = create_simulation_order_service(
            self.simulation_engine,
            self.database,
            self.start_time
        )
        
        self.inventory_service = create_simulation_inventory_service(
            self.simulation_engine,
            self.database,
            self.start_time
        )
        
        # Register services with simulation engine
        self.simulation_engine.register_service("order", self.order_service)
        self.simulation_engine.register_service("inventory", self.inventory_service)
        
        # Initialize services
        await self.order_service.startup()
        await self.inventory_service.startup()
        
        print("Services setup complete!")
    
    def setup_comprehensive_test_data(self):
        """Setup comprehensive test data with various scenarios"""
        print("Setting up comprehensive test data...")
        
        # Clear existing data
        self.database.clear_all_data()
        
        # Create products with different stock levels
        test_products = [
            {"name": "High Stock Product", "price": 10.0, "stock_quantity": 1000},
            {"name": "Medium Stock Product", "price": 25.0, "stock_quantity": 50},
            {"name": "Low Stock Product", "price": 15.0, "stock_quantity": 5},
            {"name": "Out of Stock Product", "price": 30.0, "stock_quantity": 0},
            {"name": "Single Item Product", "price": 100.0, "stock_quantity": 1},
            {"name": "Premium Product", "price": 250.0, "stock_quantity": 20}
        ]
        
        for product_data in test_products:
            self.database.create_product(product_data)
        
        print(f"Created {len(test_products)} test products")
        
        # Print initial state
        if hasattr(self.database, 'print_state'):
            self.database.print_state()
    
    async def run_scenario(self, scenario_name: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a test scenario and collect detailed results"""
        print(f"\n{'='*60}")
        print(f"RUNNING SCENARIO: {scenario_name}")
        print(f"{'='*60}")
        
        scenario_result = {
            "name": scenario_name,
            "start_time": self.time_provider.now().isoformat(),
            "actions": [],
            "errors": [],
            "performance": {},
            "final_state": {}
        }
        
        start_sim_time = self.simulation_engine.current_time
        
        for i, action in enumerate(actions):
            print(f"\n[Step {i+1}] {action['type']}")
            action_start_time = self.time_provider.now()
            
            try:
                if action["type"] == "create_order":
                    result = await self._handle_create_order_action(action)
                    
                elif action["type"] == "create_multiple_orders":
                    result = await self._handle_create_multiple_orders_action(action)
                    
                elif action["type"] == "advance_time":
                    result = await self._handle_advance_time_action(action)
                    
                elif action["type"] == "process_events":
                    result = await self._handle_process_events_action(action)
                    
                elif action["type"] == "verify_order_status":
                    result = await self._handle_verify_order_status_action(action)
                    
                elif action["type"] == "verify_inventory":
                    result = await self._handle_verify_inventory_action(action)
                    
                elif action["type"] == "add_stock":
                    result = await self._handle_add_stock_action(action)
                    
                elif action["type"] == "wait_and_process":
                    result = await self._handle_wait_and_process_action(action)
                    
                else:
                    result = {"error": f"Unknown action type: {action['type']}"}
                
                # Record successful action
                scenario_result["actions"].append({
                    "step": i + 1,
                    "type": action["type"],
                    "input": action.get("data", {}),
                    "result": result,
                    "timestamp": action_start_time.isoformat(),
                    "duration_ms": (self.time_provider.now() - action_start_time).total_seconds() * 1000
                })
                
            except Exception as e:
                error_info = {
                    "step": i + 1,
                    "action": action,
                    "error": str(e),
                    "timestamp": action_start_time.isoformat()
                }
                scenario_result["errors"].append(error_info)
                print(f"ERROR in step {i+1}: {e}")
        
        # Capture final state
        scenario_result["final_state"] = {
            "orders": self.database.get_all_orders(),
            "products": self.database.get_all_products(),
            "simulation_time": self.simulation_engine.current_time,
            "wall_clock_time": self.time_provider.now().isoformat()
        }
        
        scenario_result["performance"] = {
            "total_simulation_time": self.simulation_engine.current_time - start_sim_time,
            "total_actions": len(actions),
            "successful_actions": len(scenario_result["actions"]),
            "errors": len(scenario_result["errors"])
        }
        
        scenario_result["end_time"] = self.time_provider.now().isoformat()
        
        self.test_results.append(scenario_result)
        print(f"\n{'='*60}")
        print(f"SCENARIO COMPLETE: {scenario_name}")
        print(f"Actions: {scenario_result['performance']['successful_actions']}/{scenario_result['performance']['total_actions']}")
        print(f"Errors: {scenario_result['performance']['errors']}")
        print(f"{'='*60}")
        
        return scenario_result
    
    async def _handle_create_order_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create order action"""
        order_data = action["data"]
        order_req = OrderRequest(**order_data)
        
        result = await self.order_service.create_order(order_req)
        print(f"  Created order {result.id} for customer {result.customer_id}")
        
        return {
            "order_id": result.id,
            "status": result.status,
            "total_amount": result.total_amount
        }
    
    async def _handle_create_multiple_orders_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle creating multiple orders"""
        orders = action["data"]["orders"]
        results = []
        
        for order_data in orders:
            order_req = OrderRequest(**order_data)
            result = await self.order_service.create_order(order_req)
            results.append({
                "order_id": result.id,
                "customer_id": result.customer_id,
                "status": result.status
            })
            print(f"  Created order {result.id}")
        
        return {"created_orders": results, "count": len(results)}
    
    async def _handle_advance_time_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle time advancement"""
        seconds = action["seconds"]
        old_time = self.time_provider.now()
        self.time_provider.advance(seconds)
        new_time = self.time_provider.now()
        
        print(f"  Advanced time by {seconds} seconds: {old_time} -> {new_time}")
        
        return {
            "old_time": old_time.isoformat(),
            "new_time": new_time.isoformat(),
            "advance_seconds": seconds
        }
    
    async def _handle_process_events_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle processing simulation events"""
        max_time = action.get("max_time", 10)
        initial_sim_time = self.simulation_engine.current_time
        
        await self.simulation_engine.run_simulation(
            max_time=self.simulation_engine.current_time + max_time
        )
        
        processed_time = self.simulation_engine.current_time - initial_sim_time
        print(f"  Processed events for {processed_time} simulation time units")
        
        return {
            "initial_sim_time": initial_sim_time,
            "final_sim_time": self.simulation_engine.current_time,
            "processed_time": processed_time
        }
    
    async def _handle_verify_order_status_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle order status verification"""
        order_id = action["order_id"]
        expected_status = action.get("expected_status")
        
        order = await self.order_service.get_order(order_id)
        actual_status = order.status
        
        success = expected_status is None or actual_status == expected_status
        
        print(f"  Order {order_id} status: {actual_status}" + 
              (f" (expected: {expected_status})" if expected_status else ""))
        
        if not success:
            print(f"  ❌ STATUS MISMATCH!")
        else:
            print(f"  ✅ Status verified")
        
        return {
            "order_id": order_id,
            "actual_status": actual_status,
            "expected_status": expected_status,
            "verification_passed": success,
            "order_details": order.dict()
        }
    
    async def _handle_verify_inventory_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle inventory verification"""
        product_id = action["product_id"]
        expected_stock = action.get("expected_stock")
        
        product = await self.inventory_service.get_product(product_id)
        actual_stock = product.stock_quantity
        
        success = expected_stock is None or actual_stock == expected_stock
        
        print(f"  Product {product_id} stock: {actual_stock}" +
              (f" (expected: {expected_stock})" if expected_stock is not None else ""))
        
        if not success:
            print(f"  ❌ STOCK MISMATCH!")
        else:
            print(f"  ✅ Stock verified")
        
        return {
            "product_id": product_id,
            "actual_stock": actual_stock,
            "expected_stock": expected_stock,
            "verification_passed": success,
            "product_details": product.dict()
        }
    
    async def _handle_add_stock_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle adding stock to a product"""
        product_id = action["product_id"]
        quantity = action["quantity"]
        
        result = await self.inventory_service.update_stock(product_id, quantity)
        print(f"  Updated product {product_id} stock to {quantity}")
        
        return {
            "product_id": product_id,
            "new_stock": quantity,
            "result": result
        }
    
    async def _handle_wait_and_process_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle waiting and processing events"""
        wait_seconds = action.get("wait_seconds", 5)
        process_time = action.get("process_time", 10)
        
        # Advance time
        self.time_provider.advance(wait_seconds)
        
        # Process events
        initial_sim_time = self.simulation_engine.current_time
        await self.simulation_engine.run_simulation(
            max_time=self.simulation_engine.current_time + process_time
        )
        
        print(f"  Waited {wait_seconds}s and processed {self.simulation_engine.current_time - initial_sim_time} sim time")
        
        return {
            "wait_seconds": wait_seconds,
            "process_time": process_time,
            "simulation_time_processed": self.simulation_engine.current_time - initial_sim_time
        }
    
    def print_comprehensive_results(self):
        """Print comprehensive test results"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE SIMULATION TEST RESULTS")
        print(f"{'='*80}")
        
        total_scenarios = len(self.test_results)
        total_actions = sum(len(r["actions"]) for r in self.test_results)
        total_errors = sum(len(r["errors"]) for r in self.test_results)
        
        print(f"Total Scenarios: {total_scenarios}")
        print(f"Total Actions: {total_actions}")
        print(f"Total Errors: {total_errors}")
        print(f"Success Rate: {((total_actions - total_errors) / total_actions * 100):.1f}%")
        
        for i, result in enumerate(self.test_results, 1):
            print(f"\n{'-'*60}")
            print(f"Scenario {i}: {result['name']}")
            print(f"{'-'*60}")
            print(f"Actions: {result['performance']['successful_actions']}/{result['performance']['total_actions']}")
            print(f"Errors: {result['performance']['errors']}")
            print(f"Simulation Time: {result['performance']['total_simulation_time']}")
            
            if result["errors"]:
                print("Errors:")
                for error in result["errors"]:
                    print(f"  Step {error['step']}: {error['error']}")
            
            # Show final state summary
            orders = result["final_state"]["orders"]
            products = result["final_state"]["products"]
            
            print(f"Final State:")
            print(f"  Orders: {len(orders)}")
            
            order_status_counts = {}
            for order in orders:
                status = order["status"]
                order_status_counts[status] = order_status_counts.get(status, 0) + 1
            
            for status, count in order_status_counts.items():
                print(f"    {status}: {count}")
            
            print(f"  Products: {len(products)}")
            total_stock = sum(p["stock_quantity"] for p in products)
            print(f"    Total Stock: {total_stock}")

# Pre-defined test scenarios
async def run_comprehensive_test_suite():
    """Run a comprehensive test suite with multiple scenarios"""
    
    test_runner = ComprehensiveSimulationTest()
    await test_runner.setup_services()
    test_runner.setup_comprehensive_test_data()
    
    # Scenario 1: Basic Order Flow
    scenario1_actions = [
        {
            "type": "create_order",
            "data": {"customer_id": "customer_001", "product_id": 1, "quantity": 5}
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 2,
            "process_time": 5
        },
        {
            "type": "verify_order_status",
            "order_id": 1,
            "expected_status": "confirmed"
        },
        {
            "type": "verify_inventory",
            "product_id": 1,
            "expected_stock": 995  # 1000 - 5
        }
    ]
    
    await test_runner.run_scenario("Basic Order Flow", scenario1_actions)
    
    # Scenario 2: Insufficient Inventory
    scenario2_actions = [
        {
            "type": "create_order",
            "data": {"customer_id": "customer_002", "product_id": 3, "quantity": 10}  # Only 5 in stock
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 1,
            "process_time": 5
        },
        {
            "type": "verify_order_status",
            "order_id": 2,
            "expected_status": "rejected"
        },
        {
            "type": "verify_inventory",
            "product_id": 3,
            "expected_stock": 5  # Should remain unchanged
        }
    ]
    
    await test_runner.run_scenario("Insufficient Inventory", scenario2_actions)
    
    # Scenario 3: Multiple Concurrent Orders
    scenario3_actions = [
        {
            "type": "create_multiple_orders",
            "data": {
                "orders": [
                    {"customer_id": "customer_003", "product_id": 2, "quantity": 10},
                    {"customer_id": "customer_004", "product_id": 2, "quantity": 15},
                    {"customer_id": "customer_005", "product_id": 2, "quantity": 20},
                    {"customer_id": "customer_006", "product_id": 2, "quantity": 8}
                ]
            }
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 3,
            "process_time": 10
        },
        {
            "type": "verify_order_status",
            "order_id": 3,
            "expected_status": "confirmed"
        },
        {
            "type": "verify_order_status",
            "order_id": 4,
            "expected_status": "confirmed"
        },
        {
            "type": "verify_order_status",
            "order_id": 5,
            "expected_status": "confirmed"
        },
        {
            "type": "verify_order_status",
            "order_id": 6,
            "expected_status": "rejected"  # Should be rejected due to insufficient stock
        },
        {
            "type": "verify_inventory",
            "product_id": 2,
            "expected_stock": 5  # 50 - 10 - 15 - 20 = 5
        }
    ]
    
    await test_runner.run_scenario("Multiple Concurrent Orders", scenario3_actions)
    
    # Scenario 4: Stock Replenishment and Recovery
    scenario4_actions = [
        {
            "type": "verify_inventory",
            "product_id": 4  # Out of stock product
        },
        {
            "type": "create_order",
            "data": {"customer_id": "customer_007", "product_id": 4, "quantity": 1}
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 1,
            "process_time": 5
        },
        {
            "type": "verify_order_status",
            "order_id": 7,
            "expected_status": "rejected"
        },
        {
            "type": "add_stock",
            "product_id": 4,
            "quantity": 10
        },
        {
            "type": "create_order",
            "data": {"customer_id": "customer_008", "product_id": 4, "quantity": 3}
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 1,
            "process_time": 5
        },
        {
            "type": "verify_order_status",
            "order_id": 8,
            "expected_status": "confirmed"
        },
        {
            "type": "verify_inventory",
            "product_id": 4,
            "expected_stock": 7  # 10 - 3 = 7
        }
    ]
    
    await test_runner.run_scenario("Stock Replenishment and Recovery", scenario4_actions)
    
    # Scenario 5: Edge Cases and Error Handling
    scenario5_actions = [
        {
            "type": "create_order",
            "data": {"customer_id": "customer_009", "product_id": 999, "quantity": 1}  # Non-existent product
        },
        {
            "type": "create_order",
            "data": {"customer_id": "customer_010", "product_id": 5, "quantity": 0}  # Zero quantity
        },
        {
            "type": "create_order",
            "data": {"customer_id": "customer_011", "product_id": 5, "quantity": 2}  # Valid order
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 2,
            "process_time": 5
        },
        {
            "type": "verify_order_status",
            "order_id": 9,  # Should exist and be confirmed
            "expected_status": "confirmed"
        }
    ]
    
    await test_runner.run_scenario("Edge Cases and Error Handling", scenario5_actions)
    
    # Scenario 6: High Volume Load Test
    scenario6_actions = [
        {
            "type": "create_multiple_orders",
            "data": {
                "orders": [
                    {"customer_id": f"load_customer_{i:03d}", "product_id": 1, "quantity": 1}
                    for i in range(1, 21)  # 20 orders
                ]
            }
        },
        {
            "type": "advance_time",
            "seconds": 10
        },
        {
            "type": "process_events",
            "max_time": 20
        },
        {
            "type": "verify_inventory",
            "product_id": 1
        }
    ]
    
    await test_runner.run_scenario("High Volume Load Test", scenario6_actions)
    
    # Scenario 7: Time-Based Behavior Testing
    scenario7_actions = [
        {
            "type": "create_order",
            "data": {"customer_id": "time_customer_001", "product_id": 6, "quantity": 1}
        },
        {
            "type": "advance_time",
            "seconds": 3600  # 1 hour
        },
        {
            "type": "create_order",
            "data": {"customer_id": "time_customer_002", "product_id": 6, "quantity": 1}
        },
        {
            "type": "advance_time",
            "seconds": 86400  # 1 day
        },
        {
            "type": "create_order",
            "data": {"customer_id": "time_customer_003", "product_id": 6, "quantity": 1}
        },
        {
            "type": "process_events",
            "max_time": 30
        }
    ]
    
    await test_runner.run_scenario("Time-Based Behavior Testing", scenario7_actions)
    
    # Print comprehensive results
    test_runner.print_comprehensive_results()
    
    # Additional detailed analysis
    print(f"\n{'='*80}")
    print("DETAILED ANALYSIS")
    print(f"{'='*80}")
    
    # Analyze order patterns
    all_orders = []
    for result in test_runner.test_results:
        all_orders.extend(result["final_state"]["orders"])
    
    print(f"\nTotal Orders Created: {len(all_orders)}")
    
    status_breakdown = {}
    customer_breakdown = {}
    product_breakdown = {}
    
    for order in all_orders:
        # Status breakdown
        status = order["status"]
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        # Customer breakdown
        customer = order["customer_id"]
        customer_breakdown[customer] = customer_breakdown.get(customer, 0) + 1
        
        # Product breakdown
        product = order["product_id"]
        product_breakdown[product] = product_breakdown.get(product, 0) + 1
    
    print("\nOrder Status Breakdown:")
    for status, count in sorted(status_breakdown.items()):
        percentage = (count / len(all_orders)) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    
    print(f"\nTop 5 Customers by Order Count:")
    top_customers = sorted(customer_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
    for customer, count in top_customers:
        print(f"  {customer}: {count} orders")
    
    print(f"\nProduct Demand Analysis:")
    for product_id, count in sorted(product_breakdown.items()):
        print(f"  Product {product_id}: {count} orders")
    
    # Analyze final inventory state
    final_products = test_runner.test_results[-1]["final_state"]["products"]
    print(f"\nFinal Inventory State:")
    total_value = 0
    for product in final_products:
        value = product["price"] * product["stock_quantity"]
        total_value += value
        print(f"  Product {product['id']} ({product['name']}): {product['stock_quantity']} units, ${value:.2f} value")
    
    print(f"\nTotal Inventory Value: ${total_value:.2f}")
    
    # Performance analysis
    print(f"\nPerformance Analysis:")
    total_sim_time = sum(r["performance"]["total_simulation_time"] for r in test_runner.test_results)
    total_real_actions = sum(r["performance"]["successful_actions"] for r in test_runner.test_results)
    
    print(f"  Total Simulation Time: {total_sim_time} units")
    print(f"  Total Successful Actions: {total_real_actions}")
    print(f"  Average Actions per Scenario: {total_real_actions / len(test_runner.test_results):.1f}")
    
    if total_sim_time > 0:
        print(f"  Actions per Simulation Time Unit: {total_real_actions / total_sim_time:.2f}")
    
    # Database operation log analysis (if available)
    if hasattr(test_runner.database, 'get_operation_log'):
        operation_log = test_runner.database.get_operation_log()
        print(f"\nDatabase Operations: {len(operation_log)}")
        
        operation_types = {}
        for op in operation_log:
            op_type = op["operation"]
            operation_types[op_type] = operation_types.get(op_type, 0) + 1
        
        for op_type, count in sorted(operation_types.items()):
            print(f"  {op_type}: {count}")

# Utility functions for running specific test types
async def run_basic_test():
    """Run a basic test to verify the system works"""
    print("Running basic verification test...")
    
    test_runner = ComprehensiveSimulationTest()
    await test_runner.setup_services()
    test_runner.setup_comprehensive_test_data()
    
    basic_actions = [
        {
            "type": "create_order",
            "data": {"customer_id": "basic_test_customer", "product_id": 1, "quantity": 1}
        },
        {
            "type": "wait_and_process",
            "wait_seconds": 1,
            "process_time": 5
        },
        {
            "type": "verify_order_status",
            "order_id": 1,
            "expected_status": "confirmed"
        }
    ]
    
    result = await test_runner.run_scenario("Basic Verification Test", basic_actions)
    return result["performance"]["errors"] == 0

async def run_performance_test(num_orders: int = 100):
    """Run a performance test with specified number of orders"""
    print(f"Running performance test with {num_orders} orders...")
    
    test_runner = ComprehensiveSimulationTest()
    await test_runner.setup_services()
    test_runner.setup_comprehensive_test_data()
    
    # Create a large number of orders
    orders = [
        {"customer_id": f"perf_customer_{i:04d}", "product_id": (i % 6) + 1, "quantity": (i % 5) + 1}
        for i in range(num_orders)
    ]
    
    performance_actions = [
        {
            "type": "create_multiple_orders",
            "data": {"orders": orders}
        },
        {
            "type": "process_events",
            "max_time": 50
        }
    ]
    
    import time
    start_time = time.time()
    
    result = await test_runner.run_scenario(f"Performance Test ({num_orders} orders)", performance_actions)
    
    end_time = time.time()
    wall_clock_time = end_time - start_time
    
    print(f"\nPerformance Results:")
    print(f"  Orders Processed: {num_orders}")
    print(f"  Wall Clock Time: {wall_clock_time:.2f} seconds")
    print(f"  Orders per Second: {num_orders / wall_clock_time:.2f}")
    print(f"  Simulation Time: {result['performance']['total_simulation_time']}")
    
    return result

async def run_stress_test():
    """Run a stress test with edge cases and high load"""
    print("Running stress test...")
    
    test_runner = ComprehensiveSimulationTest()
    await test_runner.setup_services()
    test_runner.setup_comprehensive_test_data()
    
    # Stress test with various edge cases
    stress_actions = [
        # Burst of orders
        {
            "type": "create_multiple_orders",
            "data": {
                "orders": [
                    {"customer_id": f"stress_customer_{i}", "product_id": 1, "quantity": 50}
                    for i in range(10)
                ]
            }
        },
        # Process immediately
        {
            "type": "process_events",
            "max_time": 20
        },
        # Try to order out of stock items
        {
            "type": "create_multiple_orders",
            "data": {
                "orders": [
                    {"customer_id": f"late_customer_{i}", "product_id": 1, "quantity": 10}
                    for i in range(5)
                ]
            }
        },
        {
            "type": "process_events",
            "max_time": 15
        }
    ]
    
    result = await test_runner.run_scenario("Stress Test", stress_actions)
    
    # Analyze results
    orders = result["final_state"]["orders"]
    confirmed_orders = [o for o in orders if o["status"] == "confirmed"]
    rejected_orders = [o for o in orders if o["status"] == "rejected"]
    
    print(f"\nStress Test Results:")
    print(f"  Total Orders: {len(orders)}")
    print(f"  Confirmed: {len(confirmed_orders)}")
    print(f"  Rejected: {len(rejected_orders)}")
    print(f"  Success Rate: {len(confirmed_orders) / len(orders) * 100:.1f}%")
    
    return result

if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) > 1:
            test_type = sys.argv[1].lower()
            
            if test_type == "basic":
                success = await run_basic_test()
                print(f"\nBasic test {'PASSED' if success else 'FAILED'}")
                
            elif test_type == "performance":
                num_orders = int(sys.argv[2]) if len(sys.argv) > 2 else 100
                await run_performance_test(num_orders)
                
            elif test_type == "stress":
                await run_stress_test()
                
            elif test_type == "comprehensive":
                await run_comprehensive_test_suite()
                
            else:
                print(f"Unknown test type: {test_type}")
                print("Available types: basic, performance, stress, comprehensive")
        else:
            # Default to comprehensive test
            await run_comprehensive_test_suite()
    
    asyncio.run(main())