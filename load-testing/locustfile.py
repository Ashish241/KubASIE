"""
Load Testing — Locust traffic simulation for the target application.

Run with:
    locust -f locustfile.py --headless -u 100 -r 10 --run-time 10m --host http://localhost:30007
"""

import random
import math
import time

from locust import HttpUser, task, between, constant_pacing


class SteadyTrafficUser(HttpUser):
    """Simulates steady, predictable traffic."""
    wait_time = between(0.5, 2.0)
    weight = 3

    @task(5)
    def home(self):
        self.client.get("/")

    @task(3)
    def compute_light(self):
        self.client.get("/compute?intensity=2")

    @task(1)
    def compute_heavy(self):
        self.client.get("/compute?intensity=7")

    @task(2)
    def health(self):
        self.client.get("/health")


class SpikeTrafficUser(HttpUser):
    """Simulates sudden traffic spikes."""
    wait_time = constant_pacing(0.1)  # Very fast requests
    weight = 1

    @task
    def compute_burst(self):
        intensity = random.randint(3, 8)
        self.client.get(f"/compute?intensity={intensity}")


class DiurnalPatternUser(HttpUser):
    """
    Simulates day-night traffic patterns.
    Traffic follows a sinusoidal pattern based on time.
    """
    weight = 2

    def wait_time(self):
        # Vary request rate over time
        hour_in_test = (time.time() % 3600) / 3600  # 0-1 cycle per hour
        # Peak at 0.5 (30 min), low at 0 and 1
        traffic_factor = 0.5 + 0.5 * math.sin(2 * math.pi * hour_in_test - math.pi / 2)
        # Wait time inversely proportional to traffic factor
        wait = max(0.1, 3.0 * (1 - traffic_factor))
        return wait

    @task(5)
    def home(self):
        self.client.get("/")

    @task(3)
    def compute(self):
        intensity = random.choice([1, 2, 3, 5])
        self.client.get(f"/compute?intensity={intensity}")

    @task(1)
    def simulate(self):
        self.client.get("/simulate-traffic")
