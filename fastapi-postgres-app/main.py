from fastapi import FastAPI, HTTPException, Depends, Path
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import asyncpg
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()


# Pydantic models for request/response
class AddressInput(BaseModel):
    type: str = Field(..., pattern="^(billing|shipping)$")
    first_name: str
    last_name: str
    company: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state_province: str
    postal_code: str
    country: str = "US"  # ISO country code
    phone: Optional[str] = None
    is_default: bool = False


class UserInput(BaseModel):
    email: EmailStr
    password: str  # In production, this should be hashed before storage
    first_name: str
    last_name: str
    phone: Optional[str] = None
    addresses: List[AddressInput]


class OrderItemInput(BaseModel):
    product_id: UUID
    sku: str
    name: str
    price: Decimal
    variant_id: Optional[UUID] = None
    quantity: int = Field(gt=0)


class OrderInput(BaseModel):
    user: UserInput
    items: List[OrderItemInput]
    shipping_address_index: int = 0
    billing_address_index: int = 0
    payment_method: Optional[str] = "credit_card"
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: UUID
    order_number: str
    user_id: UUID
    total_amount: Decimal
    status: str
    payment_status: str
    created_at: datetime
    items_count: int


class OrderStatusUpdate(BaseModel):
    status: str


class AddressUpdate(BaseModel):
    address_id: UUID
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None


# Database connection pool
class Database:
    pool: Optional[asyncpg.Pool] = None


db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ecommerce"),
        min_size=10,
        max_size=20,
    )
    yield
    # Shutdown
    await db.pool.close()


app = FastAPI(title="Order Management API", lifespan=lifespan)


async def get_db_pool():
    return db.pool


@app.post("/orders", response_model=OrderResponse)
async def create_order(
    order_input: OrderInput, pool: asyncpg.Pool = Depends(get_db_pool)
):
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                # Upsert user
                user_id = await conn.fetchval(
                    """
                    INSERT INTO users (email, password_hash, first_name, last_name, phone)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (email) 
                    DO UPDATE SET 
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        phone = COALESCE(EXCLUDED.phone, users.phone)
                    RETURNING id
                    """,
                    order_input.user.email,
                    order_input.user.password,  # In production, hash this
                    order_input.user.first_name,
                    order_input.user.last_name,
                    order_input.user.phone,
                )

                # Upsert addresses
                address_ids = []
                for addr in order_input.user.addresses:
                    address_id = await conn.fetchval(
                        """
                        INSERT INTO addresses (
                            user_id, type, first_name, last_name, company,
                            address_line_1, address_line_2, city, state_province,
                            postal_code, country, phone, is_default
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT (user_id, type, address_line_1, city, state_province, postal_code, country)
                        DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            company = EXCLUDED.company,
                            address_line_2 = EXCLUDED.address_line_2,
                            phone = EXCLUDED.phone,
                            is_default = EXCLUDED.is_default,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                        """,
                        user_id,
                        addr.type,
                        addr.first_name,
                        addr.last_name,
                        addr.company,
                        addr.address_line_1,
                        addr.address_line_2,
                        addr.city,
                        addr.state_province,
                        addr.postal_code,
                        addr.country,
                        addr.phone,
                        addr.is_default,
                    )
                    address_ids.append(address_id)

                # Validate address indices
                if order_input.shipping_address_index >= len(address_ids):
                    raise ValueError("Invalid shipping address index")
                if order_input.billing_address_index >= len(address_ids):
                    raise ValueError("Invalid billing address index")

                # Upsert products and calculate totals
                subtotal = Decimal("0")
                for item in order_input.items:
                    product = await conn.fetchrow(
                        """
                        INSERT INTO products (id, name, sku, price)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (sku)
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            price = EXCLUDED.price,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id, price
                        """,
                        item.product_id,
                        item.name,
                        item.sku,
                        item.price,
                    )
                    if not product:
                        raise HTTPException(status_code=404, detail="Product not found")
                    subtotal += product["price"] * item.quantity

                total_amount = subtotal  # Add tax and shipping logic as needed

                # Create order
                order_number = f"ORD-{int(datetime.utcnow().timestamp() * 1000)}"
                order_id = await conn.fetchval(
                    """
                    INSERT INTO orders 
                    (user_id, order_number, subtotal, tax_amount, shipping_amount, total_amount, status, payment_status, payment_method)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    user_id,
                    order_number,
                    subtotal,
                    Decimal("0.00"),
                    Decimal("0.00"),
                    total_amount,
                    "pending",
                    "pending",
                    order_input.payment_method,
                )

                return OrderResponse(
                    order_id=order_id,
                    order_number=order_number,
                    user_id=user_id,
                    total_amount=total_amount,
                    status="pending",
                    payment_status="pending",
                    created_at=datetime.now(),
                    items_count=len(order_input.items),
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Welcome to the Order Management API"}


@app.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    valid_statuses = [
        "pending",
        "confirmed",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
        "refunded",
    ]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE orders SET status=$1, updated_at=NOW() WHERE id=$2",
            status_update.status,
            order_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, "new_status": status_update.status}


@app.get("/orders/{order_id}/status")
async def get_order_status(
    order_id: UUID,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT status FROM orders WHERE id=$1", order_id)
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return {"order_id": order_id, "status": row["status"]}
