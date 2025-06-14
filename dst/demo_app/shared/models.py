from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, rejected, failed
    total_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = relationship("Product")

# Database setup
import os

def get_database_url():
    """Get database URL with proper path handling"""
    db_path = os.getenv("DB_PATH", "/app/data/simulation.db")
    
    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"Created database directory: {db_dir}")
    
    # Check if we can write to the directory
    if not os.access(db_dir, os.W_OK):
        print(f"Warning: No write access to {db_dir}")
    
    return f"sqlite:///{db_path}"

# Initialize database connection
database_url = get_database_url()
print(f"Using database URL: {database_url}")

engine = create_engine(database_url, echo=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    try:
        print("Initializing database...")
        # Test basic connectivity first
        with engine.connect() as conn:
            print("Database connection test successful")
        
        # Create tables
        Base.metadata.create_all(engine)
        print("Database tables created successfully")
        return True
    except Exception as e:
        print(f"Error creating database tables: {e}")
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database at module level (not in async startup)
print("Starting database initialization...")
if not init_db():
    print("Failed to initialize database!")
    exit(1)