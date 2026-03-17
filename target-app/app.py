"""
Target Flask Application — Kubernetes Auto-Scaling Intelligence Engine

A realistic microservice instrumented with Prometheus metrics.
Used as the workload that the Intelligence Engine auto-scales.
"""

import time
import math
import random
from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# ── Prometheus Metrics ───────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "app_request_total",
    "Total number of requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "app_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Auto-instrument all Flask routes (request count, latency histograms)
metrics = PrometheusMetrics(app, path=None)  # path=None: we expose /metrics ourselves below


# ── Health & Readiness ───────────────────────────────────────────────
@app.route("/health")
def health():
    """Liveness probe — is the process alive?"""
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
def ready():
    """Readiness probe — is the app ready to receive traffic?"""
    return jsonify({"status": "ready"}), 200


# ── Main Endpoints ───────────────────────────────────────────────────
@app.route("/")
def home():
    """Root endpoint returning a welcome message."""
    start = time.time()
    response = jsonify({
        "service": "target-app",
        "version": "1.0.0",
        "message": "Kubernetes Auto-Scaling Intelligence Engine — Target Workload",
    })
    REQUEST_COUNT.labels(method="GET", endpoint="/", http_status=200).inc()
    REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)
    return response, 200


@app.route("/compute")
def compute():
    """
    CPU-intensive endpoint for simulating real workloads.
    Query params:
      - intensity: 1-10 (default 5) — controls computation duration
    """
    start = time.time()
    intensity = int(request.args.get("intensity", 5))
    intensity = max(1, min(10, intensity))  # clamp 1-10

    # Simulate CPU work — matrix-like operations
    result = 0.0
    iterations = intensity * 50_000
    for i in range(iterations):
        result += math.sin(i * 0.001) * math.cos(i * 0.002)

    latency = time.time() - start
    REQUEST_COUNT.labels(method="GET", endpoint="/compute", http_status=200).inc()
    REQUEST_LATENCY.labels(endpoint="/compute").observe(latency)

    return jsonify({
        "intensity": intensity,
        "iterations": iterations,
        "result": round(result, 4),
        "latency_ms": round(latency * 1000, 2),
    }), 200


@app.route("/simulate-traffic")
def simulate_traffic():
    """
    Endpoint that introduces random latency to simulate variable traffic.
    Useful for testing the ML predictor's ability to forecast patterns.
    """
    start = time.time()
    # Random sleep between 10ms and 500ms
    sleep_time = random.uniform(0.01, 0.5)
    time.sleep(sleep_time)

    latency = time.time() - start
    REQUEST_COUNT.labels(method="GET", endpoint="/simulate-traffic", http_status=200).inc()
    REQUEST_LATENCY.labels(endpoint="/simulate-traffic").observe(latency)

    return jsonify({
        "simulated_delay_ms": round(sleep_time * 1000, 2),
        "total_latency_ms": round(latency * 1000, 2),
    }), 200


@app.route("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# ── Entry Point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
