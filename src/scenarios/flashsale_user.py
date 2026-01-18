import logging
from locust import HttpUser, task, between
from locust.exception import StopUser

# Initialize logger for standard output debugging
logger = logging.getLogger(__name__)

class FlashSaleUser(HttpUser):
    # Simulate realistic user "think time" to prevent DDoS behavior
    # User will wait 1-5 seconds between actions
    wait_time = between(1, 5)

    def on_start(self):
        """
        Executed once when the User is spawned. 
        Ideal for authentication (Login/Token Retrieval).
        """
        logger.info("User spawned! Preparing to login...")
        # TODO
        pass
    
    @task(3)
    def browse_product(self):
        """
        Scenario: User browses product details.
        Weight (3): This action occurs 3x more frequently than checkout.
        """
        # Using self.client (Requests Wrapper) to hit dummy endpoint
        with self.client.get("/api/v1/products/flash_sale", catch_response=True) as response:
            if response.status_code == 200:
                # Successful load - no action needed
                pass
            else:
                response.failure(f"Failed to load product: {response.status_code}")

    @task(1)
    def attempt_checkout(self):
        """
        Scenario: User attempts to purchase the item.
        Weight (1): Represents the conversion funnel
        """

    payload = {"product_id": "123", "qty": 1}

    # Simulate 'Buy Now' button click
    with self.client.post("/api/v1/checkout", json=payload, catch_response=True) as response:
        if response.status_code == 201:
            logger.info("Checkout successful!")
        elif response.status_code == 404:
            # Business Logic Assertion: Handle expected failures (e.g., Out of Stock)
            response.failure("Product sold out!")
        else:
            response.failure(f"Checkout Error. Status: {response.status_code}")

    def on_stop(self):
        """
        Executed when the test stops or the user is killed.
        Useful for teardown (logging out, cleaning data).
        """
        logger.info("User stopped.")