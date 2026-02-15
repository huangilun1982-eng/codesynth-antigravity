import time
import logging

class CircuitBreaker:
    """自動監控連續失敗次數 (Rule 8)"""
    def __init__(self, name, max_failures=3, reset_timeout=60):
        self.name = name
        self.failures = 0
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN

    def can_execute(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                logging.info(f"CIRCUIT: {self.name} attempting reset.")
                return True
            return False
        return True

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.max_failures:
            self.state = "OPEN"
            self.last_failure_time = time.time()
            logging.critical(f"CIRCUIT: {self.name} is now OPEN (Disabled)")

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"