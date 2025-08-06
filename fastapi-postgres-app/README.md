# FastAPI PostgreSQL Application

This project is a FastAPI application that interacts with a PostgreSQL database. It provides a simple API for managing orders, including adding new orders to the database.

## Project Structure

```
fastapi-postgres-app
├── .env                  # Environment variables for the application
├── .gitignore            # Files and directories to ignore in version control
├── docker-compose.yml     # Docker Compose configuration for services
├── main.py               # Entry point for the FastAPI application
├── requirements.txt      # Python dependencies for the project
├── init-scripts
│   └── schema.sql       # SQL commands to set up the database schema
├── README.md             # Documentation for the project
└── .vscode
    ├── launch.json       # Debugging configuration for Visual Studio Code
    └── settings.json     # Workspace-specific settings for Visual Studio Code
```

## Setup Instructions

1. **Clone the repository:**

   ```
   git clone <repository-url>
   cd fastapi-postgres-app
   ```

2. **Create a `.env` file:**
   Populate the `.env` file with your database connection details. Example:

   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   DB_NAME=ecommerce
   ```

3. **Install dependencies:**
   Make sure you have Python and pip installed. Then run:

   ```
   pip install -r requirements.txt
   ```

4. **Run the application with Docker:**
   Use Docker Compose to start the PostgreSQL database and the FastAPI application:

   ```
   docker-compose up
   ```

5. **Access the API:**
   The FastAPI application will be available at `http://localhost:8000`. You can access the API documentation at `http://localhost:8000/docs`.

## Usage Example

To create a new order, send a POST request to `/orders` with a JSON payload like:

```json
{
  "user": {
    "email": "customer@example.com",
    "password": "securepassword",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "1234567890",
    "addresses": [
      {
        "type": "shipping",
        "first_name": "John",
        "last_name": "Doe",
        "address_line_1": "123 Main St",
        "city": "New York",
        "state_province": "NY",
        "postal_code": "10001",
        "country": "US",
        "is_default": true
      },
      {
        "type": "billing",
        "first_name": "John",
        "last_name": "Doe",
        "address_line_1": "123 Main St",
        "city": "New York",
        "state_province": "NY",
        "postal_code": "10001",
        "country": "US",
        "is_default": true
      }
    ]
  },
  "items": [
    {
      "product_id": "a-valid-product-uuid",
      "quantity": 2
    }
  ],
  "shipping_address_index": 0,
  "billing_address_index": 1,
  "payment_method": "credit_card",
  "notes": "Please deliver between 9am-5pm"
}
```

You can use [httpie](https://httpie.io/) or [curl](https://curl.se/) to test:

```sh
http POST http://localhost:8000/orders < order.json
```

or

```sh
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d @order.json
```

Replace `"a-valid-product-uuid"` with an actual product UUID from your
