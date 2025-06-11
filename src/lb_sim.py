from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional

class EventType(Enum):
    REQUEST_ARRIVAL = "request_arrival"
    REQUEST_COMPLETION = "request_completion"
    HEALTH_CHECK = "health_check"

@dataclass
class Event:
    time: float
    event_type: EventType
    data: Dict

class BackendServer:
    def __init__(self, server_id: str, capacity: int, processing_time_dist):
        self.server_id = server_id
        self.capacity = capacity
        self.current_load = 0
        self.queue = []
        self.is_healthy = True
        self.processing_time_dist = processing_time_dist
        self.total_requests = 0
        self.total_response_time = 0.0

class NginxLoadBalancer:
    def __init__(self, servers: List[BackendServer], algorithm: str = "round_robin"):
        self.servers = servers
        self.algorithm = algorithm
        self.round_robin_index = 0
        self.event_queue = []
        self.current_time = 0.0
        self.stats = {
            'total_requests': 0,
            'dropped_requests': 0,
            'average_response_time': 0.0
        }
