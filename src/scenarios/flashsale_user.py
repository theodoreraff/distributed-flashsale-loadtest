import logging
from locust import HttpUser, task, between

# Setup simple logging
logger = logging.getLogger(__name__)


class FlashSaleUser(HttpUser):
    """
    Simulates a real user behaviour during a Flash Sale.

    Behavior:
    1. Browses product (Frequently).
    2. Attempts to Checkout (Less frequently, but critical).
    """

    # "Think Time": Users wait 1-5 seconds between actions.
    # This makes the traffic look more natural, not like a DDoS attack.
    wait_time = between(1, 5)

    def on_start(self):
        """Executed when a new simulated user is spawned."""
        pass

    @task(3)
    def browse_product(self):
        """
        Action: View Product Details.
        Weight: 3 (Users browse more often than they buy).
        """
        with self.client.get("/api/v1/products/flash-sale", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to load page: {response.status_code}")

    @task(1)
    def attempt_checkout(self):
        """
        Action: Click 'Buy Now'.
        This is the critical path where Race Conditions happen.
        """

        # CHANGE THIS URL TO TEST DIFFERENT SCENARIOS:
        # 1. /api/v1/checkout/buggy    -> Expect Negative Stock (Overselling)
        # 2. /api/v1/checkout/safe     -> Expect 0 Stock (Correct)
        # 3. /api/v1/checkout/unstable -> Expect Random Errors
        target_url = "/api/v1/checkout/buggy"

        payload = {"product_id": "123", "qty": 1}

        with self.client.post(target_url, json=payload, catch_response=True) as response:

            # Case 1: Purchase Successful (HTTP 200/201)
            if response.status_code in [200, 201]:
                response.success()

            # Case 2: Product Sold Out (HTTP 404)
            # This is a VALID business scenario, not a system error.
            elif response.status_code == 404:
                response.failure("Product Sold Out (Expected)")

            # Case 3: System Error (HTTP 500, 503, etc.)
            # This is an actual bug or server crash.
            else:
                response.failure(f"System Error: {response.status_code}")

    def on_stop(self):
        """Executed when the user is stopped."""
        pass