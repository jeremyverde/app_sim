import heapq
import random
import heapq
from lb_sim import Event, EventType, BackendServer


class TrafficGenerator:
    def __init__(self, arrival_rate_dist, request_size_dist):
        self.arrival_rate_dist = arrival_rate_dist
        self.request_size_dist = request_size_dist
        self.event_queue = []
        self.current_time = 0.0
        self.algorithm = "round_robin"  # Default load balancing algorithm
        self.servers = [
            BackendServer(server_id=f"server_{i}", capacity=10, processing_time_dist=random.choice(request_size_dist))
            for i in range(3)  # Example with 3 backend servers
        ]
        self.round_robin_index = 0
        self.total_response_time = 0.0
        self.stats = {
            'total_requests': 0,
            'dropped_requests': 0,
            'total_response_time': 0.0
        }

    def select_server_round_robin(self):
        healthy_servers = [s for s in self.servers if s.is_healthy]
        if not healthy_servers:
            return None
        
        server = healthy_servers[self.round_robin_index % len(healthy_servers)]
        self.round_robin_index += 1
        return server

    def select_server_least_connections(self):
        healthy_servers = [s for s in self.servers if s.is_healthy]
        if not healthy_servers:
            return None
        
        return min(healthy_servers, key=lambda s: s.current_load)
    
    def handle_request_arrival(self, event):
        self.stats['total_requests'] += 1
        
        # Select backend server using configured algorithm
        if self.algorithm == "round_robin":
            server = self.select_server_round_robin()
        elif self.algorithm == "least_connections":
            server = self.select_server_least_connections()
        
        if not server or server.current_load >= server.capacity:
            # Request dropped or queued based on configuration
            self.stats['dropped_requests'] += 1
            return
        
        # Process request
        processing_time = server.processing_time_dist
        completion_time = self.current_time + processing_time
        self.stats['total_response_time'] += processing_time
        
        server.current_load += 1
        server.queue.append(event.data['request_id'])
        
        # Schedule completion event
        completion_event = Event(
            time=completion_time,
            event_type=EventType.REQUEST_COMPLETION,
            data={'server_id': server.server_id, 'request_id': event.data['request_id']}
        )
        heapq.heappush(self.event_queue, (completion_time, completion_event))

    def handle_request_completion(self, event):
        server_id = event.data['server_id']
        server = next(s for s in self.servers if s.server_id == server_id)
        
        server.current_load -= 1
        server.queue.remove(event.data['request_id'])
        
        # Update statistics
        response_time = self.current_time - event.data.get('arrival_time', 0)
        server.total_requests += 1
        server.total_response_time += response_time
    
    def generate_next_arrival(self, current_time):
        # Exponential inter-arrival times for Poisson process
        inter_arrival_time = random.expovariate(self.arrival_rate_dist)
        return current_time + inter_arrival_time

    def run_simulation(self, duration):
        # Initialize with first request arrival
        first_arrival = self.generate_next_arrival(0)
        heapq.heappush(self.event_queue, (first_arrival, 
            Event(first_arrival, EventType.REQUEST_ARRIVAL, {'request_id': 1})))
        
        while self.current_time < duration and self.event_queue:
            event_time, event = heapq.heappop(self.event_queue)
            self.current_time = event_time
            
            if event.event_type == EventType.REQUEST_ARRIVAL:
                self.handle_request_arrival(event)
                # Schedule next arrival
                next_arrival = self.generate_next_arrival(event_time)
                if next_arrival < duration:
                    heapq.heappush(self.event_queue, (next_arrival,
                        Event(next_arrival, EventType.REQUEST_ARRIVAL, 
                            {'request_id': self.stats['total_requests'] + 1})))
            
            elif event.event_type == EventType.REQUEST_COMPLETION:
                self.handle_request_completion(event)

if __name__ == "__main__":
    sim = TrafficGenerator(
        arrival_rate_dist=1.0,  # Mean arrival rate of 1 request per second
        request_size_dist=[100,105,135,1000,800,200,100]  # Request size between 100 and 1000 bytes
    )
    sim.run_simulation(60)  # Run for 60 seconds
    print(f"Total requests: {sim.stats['total_requests']}")
    print(f"Dropped requests: {sim.stats['dropped_requests']}")
    print(f"Average response time: {sim.stats['total_response_time'] / sim.stats['total_requests'] if sim.stats['total_requests'] > 0 else 0:.2f} seconds")
    print(f"Server stats: {[{'id': s.server_id, 'load': s.current_load, 'requests': s.total_requests} for s in sim.servers]}")
    print("Simulation completed.")
