from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from shared.models import get_db, Product
from shared.message_queue import MessageQueue
import asyncio

app = FastAPI(title="Inventory Service")
mq = MessageQueue()

class ProductCreate(BaseModel):
    name: str
    price: float
    stock_quantity: int

class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    stock_quantity: int

@app.on_event("startup")
async def startup():
    print("Inventory service starting up...")
    # Subscribe to order events
    await mq.subscribe("order_received", handle_order_received)
    print("Inventory service startup complete!")

@app.post("/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return ProductResponse(
        id=db_product.id,
        name=db_product.name,
        price=db_product.price,
        stock_quantity=db_product.stock_quantity
    )

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product details"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        price=product.price,
        stock_quantity=product.stock_quantity
    )

@app.put("/products/{product_id}/stock")
async def update_stock(product_id: int, quantity: int, db: Session = Depends(get_db)):
    """Update product stock (for testing setup)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.stock_quantity = quantity
    db.commit()
    
    return {"message": f"Stock updated to {quantity}"}

async def handle_order_received(message: dict, db: Session = Depends(get_db)):
    """Handle incoming order events and check inventory"""
    order_id = message.get("order_id")
    product_id = message.get("product_id")
    quantity = message.get("quantity")
    
    print(f"Processing inventory check for order {order_id}")
    
    # Check and reserve inventory
    
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if product and product.stock_quantity >= quantity:
            # Reserve inventory (decrement stock)
            product.stock_quantity -= quantity
            db.commit()
            available = True
            print(f"Reserved {quantity} units of product {product_id}")
        else:
            available = False
            print(f"Insufficient stock for product {product_id}")
        
        # Publish inventory check result
        await mq.publish("inventory_checked", {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "available": available,
            "remaining_stock": product.stock_quantity if product else 0
        })
        
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)