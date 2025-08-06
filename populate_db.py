import uuid
import random
import time
import httpx

API_URL = "http://localhost:8000"

# Generate 12 products
products = [
    {
        "id": str(uuid.uuid4()),
        "name": f"Product {i}",
        "sku": f"SKU-{1000+i}",
        "price": round(random.uniform(10, 100), 2),
    }
    for i in range(12)
]

# Generate 12 users
users = [
    {
        "email": f"user{i}@example.com",
        "password": "password123",
        "first_name": f"First{i}",
        "last_name": f"Last{i}",
        "phone": f"555-010{i:02d}",
        "addresses": [
            {
                "type": "shipping",
                "first_name": f"First{i}",
                "last_name": f"Last{i}",
                "address_line_1": f"{i} Main St",
                "city": "Cityville",
                "state_province": "State",
                "postal_code": f"100{i:02d}",
                "country": "US",
                "is_default": True,
            },
            {
                "type": "billing",
                "first_name": f"First{i}",
                "last_name": f"Last{i}",
                "address_line_1": f"{i} Main St",
                "city": "Cityville",
                "state_province": "State",
                "postal_code": f"100{i:02d}",
                "country": "US",
                "is_default": True,
            },
        ],
    }
    for i in range(12)
]


def make_order_payload(user, product, quantity):
    return {
        "user": user,
        "items": [
            {
                "product_id": product["id"],
                "sku": product["sku"],
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
            }
        ],
        "shipping_address_index": 0,
        "billing_address_index": 1,
        "payment_method": "credit_card",
        "notes": "Automated test order",
    }


def update_order_status(order_id, new_status):
    resp = httpx.patch(
        f"{API_URL}/orders/{order_id}/status", json={"status": new_status}
    )
    print(
        f"Update order {order_id} status to {new_status}: {resp.status_code} - {resp.text}"
    )


def get_order_status(order_id):
    resp = httpx.get(f"{API_URL}/orders/{order_id}/status")
    print(f"Get order {order_id} status: {resp.status_code} - {resp.text}")
    return resp


def populate_db(num_calls=12, interval_sec=1):
    status_progression = ["confirmed", "processing", "shipped", "delivered"]
    for i in range(num_calls):
        user = random.choice(users)
        product = random.choice(products)
        quantity = random.randint(1, 10)
        payload = make_order_payload(user, product, quantity)
        order_id = None
        try:
            response = httpx.post(f"{API_URL}/orders", json=payload)
            print(f"Order {i+1}: Status {response.status_code} - {response.text}")
            if response.status_code == 200:
                data = response.json()
                order_id = data["order_id"]
        except Exception as e:
            print(f"Order {i+1}: Error - {e}")

        if order_id:
            for status in status_progression:
                update_order_status(order_id, status)
                time.sleep(0.5)

        time.sleep(interval_sec)


if __name__ == "__main__":
    populate_db(num_calls=12, interval_sec=1)
    print("Database population complete.")
