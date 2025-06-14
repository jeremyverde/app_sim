import redis
import json
import asyncio
from typing import Dict, Any, Callable
import uuid
import os
from datetime import datetime
import threading

class MessageQueue:
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        print(f"Connecting to Redis at: {redis_url}")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.subscribers = {}
        
        # Test connection
        try:
            self.redis.ping()
            print("Redis connection successful!")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            raise
    
    async def publish(self, channel: str, message: Dict[Any, Any]):
        """Publish a message to a channel"""
        message_id = str(uuid.uuid4())
        message_with_id = {
            "id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
            **message
        }
        # Use asyncio to run the blocking redis call in a thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.redis.publish, channel, json.dumps(message_with_id))
        print(f"Published to {channel}: {message_with_id}")
        return message_id
    
    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe to a channel with a message handler"""
        try:
            print(f"Setting up subscription to {channel}")
            
            # Start the listener in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            thread = threading.Thread(
                target=self._start_listener_thread,
                args=(channel, handler, loop),
                daemon=True
            )
            thread.start()
            
            print(f"Subscribed to {channel}")
        except Exception as e:
            print(f"Error subscribing to {channel}: {e}")
            raise
    
    def _start_listener_thread(self, channel: str, handler: Callable, loop):
        """Start Redis listener in a separate thread"""
        try:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(channel)
            print(f"Started listener thread for {channel}")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        # Schedule the handler to run in the main event loop
                        asyncio.run_coroutine_threadsafe(handler(data), loop)
                    except Exception as e:
                        print(f"Error handling message in {channel}: {e}")
        except Exception as e:
            print(f"Error in listener thread for {channel}: {e}")