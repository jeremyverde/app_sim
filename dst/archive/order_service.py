from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from shared.models import get_db, Order, Product
from shared.message_queue import MessageQueue
import asyncio

app = FastAPI(title="Order Service")
mq = MessageQueue()

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

@app.on_event("startup")
async def startup():
    print("Order service starting up...")
    # Subscribe to inventory responses
    await mq.subscribe("inventory_checked", handle_inventory_response)
    print("Order service startup complete!")

@app.post("/orders", response_model=OrderResponse)
async def create_order(order_req: OrderRequest, db: Session = Depends(get_db)):
    """Create a new order and trigger inventory check"""
    
    # Validate product exists
    product = db.query(Product).filter(Product.id == order_req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate total
    total_amount = product.price * order_req.quantity
    
    # Create order in pending state
    order = Order(
        customer_id=order_req.customer_id,
        product_id=order_req.product_id,
        quantity=order_req.quantity,
        total_amount=total_amount,
        status="pending"
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Publish order created event
    await mq.publish("order_received", {
        "order_id": order.id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "customer_id": order.customer_id
    })
    
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        product_id=order.product_id,
        quantity=order.quantity,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at.isoformat()
    )

@app.get("/orders/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get order status"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        product_id=order.product_id,
        quantity=order.quantity,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at.isoformat()
    )

async def handle_inventory_response(message: dict, db: Session = Depends(get_db)):
    """Handle inventory check responses"""
    order_id = message.get("order_id")
    available = message.get("available", False)
    
    # Update order status based on inventory check
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = "confirmed" if available else "rejected"
            db.commit()
            print(f"Order {order_id} status updated to: {order.status}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)