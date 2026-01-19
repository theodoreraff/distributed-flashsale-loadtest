from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import random
import threading

# Metadata for Swagger UI
app = FastAPI(
    title="Flash Sale Simulation API",
    description="A Mock API to demonstrate Race Conditions and Thread Safety.",
    version="1.0.0"
)

# --- SHARED STATE (SIMULATED DATABASE) ---
# In a real app, this would be Redis or PostgreSQL.
# We use a global variable to simulate a shared inventory.
GLOBAL_STOCK = 100

# Mutex Lock: This is the solution for Thread Safety.
# It forces requests to "queue up" one by one.
stock_lock = threading.Lock()


class CheckoutRequest(BaseModel):
    product_id: str
    qty: int


# ==========================================
# 1. HELPER ENDPOINTS
# ==========================================

@app.get("/")
def health_check():
    """
    Simple health check to verify if the server is running.
    """
    return {"status": "SystemOnline", "current_stock": GLOBAL_STOCK}


@app.get("/api/v1/products/flash-sale")
def get_product_details():
    """
    Simulates a user viewing the product page.
    This endpoint is used to generate 'Browse' traffic in the load test.
    """
    return {
        "id": "123",
        "name": "Gaming Laptop ROG",
        "stock": GLOBAL_STOCK,  # Returns the current real-time stock
        "price": 15000000
    }


@app.get("/api/v1/debug/stock")
def get_current_stock():
    """
    Debug Endpoint: Checks the final stock after the load test.
    If this returns a NEGATIVE number, it means the Race Condition happened.
    """
    return {"final_stock": GLOBAL_STOCK}


@app.post("/api/v1/debug/reset")
def reset_inventory():
    """
    Resets the stock back to 100.
    Useful for restarting the test without restarting the Docker container.
    """
    global GLOBAL_STOCK
    GLOBAL_STOCK = 100
    return {"message": "Stock reset to 100"}


# ==========================================
# 2. THE EXPERIMENT SCENARIOS
# ==========================================

@app.post("/api/v1/checkout/buggy")
def process_checkout_buggy(order: CheckoutRequest):
    """
    SCENARIO A: The Vulnerable Endpoint.

    This function has a 'Race Condition' bug.
    Logic:
    1. Check if stock > 0.
    2. Wait for 0.01s (Simulating Database Latency).
    3. Decrease stock.

    Why it fails:
    If 1000 users enter step 1 at the same time, they all see stock > 0.
    They all proceed to step 3, making the stock negative (Overselling).
    """
    global GLOBAL_STOCK

    if GLOBAL_STOCK > 0:
        # Simulate DB processing time. This gap allows other threads to enter.
        time.sleep(0.01)

        GLOBAL_STOCK -= 1
        return {"status": "success", "remaining_stock": GLOBAL_STOCK}

    raise HTTPException(status_code=404, detail="Product Sold Out")


@app.post("/api/v1/checkout/unstable")
def process_checkout_unstable(order: CheckoutRequest):
    """
    SCENARIO B: Chaos Engineering (Random Failures).

    Simulates a server under heavy load that randomly crashes or times out.
    - 5% chance to return HTTP 503 (Service Unavailable).
    - 95% chance to proceed with the 'buggy' logic.
    """
    # Randomly fail 5% of the requests
    if random.random() < 0.05:
        raise HTTPException(status_code=503, detail="Server Busy / Timeout")

    global GLOBAL_STOCK
    if GLOBAL_STOCK > 0:
        GLOBAL_STOCK -= 1
        return {"status": "success", "remaining_stock": GLOBAL_STOCK}

    raise HTTPException(status_code=404, detail="Product Sold Out")


@app.post("/api/v1/checkout/safe")
def process_checkout_safe(order: CheckoutRequest):
    """
    SCENARIO C: The Fixed Endpoint (Thread Safe).

    This function uses a 'Mutex Lock' (threading.Lock).

    How it works:
    - Only ONE thread can enter the 'with stock_lock' block at a time.
    - Other threads must wait in line until the previous thread finishes.
    - This ensures the stock is updated accurately, even with 1000 users.
    """
    global GLOBAL_STOCK

    # Critical Section: Locked for safety
    with stock_lock:
        if GLOBAL_STOCK > 0:
            time.sleep(0.01)
            GLOBAL_STOCK -= 1
            return {"status": "success", "remaining_stock": GLOBAL_STOCK}

    raise HTTPException(status_code=404, detail="Product Sold Out")