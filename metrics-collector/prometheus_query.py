"""
Prometheus Query Client — PromQL query builder & executor.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger("metrics-collector.prometheus")


class PrometheusQuerier:
    """Executes PromQL queries against Prometheus HTTP API."""

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _query(self, promql: str) -> Optional[float]:
        """Execute an instant query and return the scalar result."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": promql},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            if data["status"] != "success":
                logger.warning("Prometheus query failed: %s", data)
                return None

            results = data["data"]["result"]
            if not results:
                logger.debug("No data for query: %s", promql)
                return 0.0

            # Return the first result's value
            return float(results[0]["value"][1])

        except Exception as e:
            logger.error("Prometheus request failed: %s", e)
            return None

    def _query_range(self, promql: str, start: str, end: str, step: str) -> list:
        """Execute a range query and return time-series data."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": promql,
                    "start": start,
                    "end": end,
                    "step": step,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            if data["status"] != "success":
                logger.warning("Range query failed: %s", data)
                return []

            results = data["data"]["result"]
            if not results:
                return []

            # Return list of (timestamp, value) tuples
            return [
                (float(ts), float(val))
                for ts, val in results[0]["values"]
            ]

        except requests.RequestException as e:
            logger.error("Prometheus range request failed: %s", e)
            return []

    # ── Application Metrics ──────────────────────────────────────────

    def get_request_rate(self, job: str, window: str = "5m") -> Optional[float]:
        """Get requests per second over the given window."""
        query = f'sum(rate(app_request_total{{job="{job}"}}[{window}]))'
        return self._query(query)

    def get_latency_percentile(
        self, job: str, quantile: float = 0.99, window: str = "5m"
    ) -> Optional[float]:
        """Get request latency at the specified percentile."""
        query = (
            f'histogram_quantile({quantile}, '
            f'sum(rate(app_request_latency_seconds_bucket{{job="{job}"}}[{window}])) '
            f'by (le))'
        )
        return self._query(query)

    # ── Cluster Resource Metrics ─────────────────────────────────────

    def get_cpu_utilization(
        self, namespace: str, deployment: str
    ) -> Optional[float]:
        """Get average CPU utilization (%) for a deployment."""
        query = (
            f'100 * avg('
            f'rate(container_cpu_usage_seconds_total{{'
            f'namespace="{namespace}", '
            f'pod=~"{deployment}-.*", '
            f'container!="POD", container!=""'
            f'}}[5m])'
            f') / avg('
            f'kube_pod_container_resource_requests{{'
            f'namespace="{namespace}", '
            f'pod=~"{deployment}-.*", '
            f'resource="cpu"'
            f'}})'
        )
        return self._query(query)

    def get_memory_utilization(
        self, namespace: str, deployment: str
    ) -> Optional[float]:
        """Get average memory utilization (%) for a deployment."""
        query = (
            f'100 * avg('
            f'container_memory_working_set_bytes{{'
            f'namespace="{namespace}", '
            f'pod=~"{deployment}-.*", '
            f'container!="POD", container!=""'
            f'}}'
            f') / avg('
            f'kube_pod_container_resource_requests{{'
            f'namespace="{namespace}", '
            f'pod=~"{deployment}-.*", '
            f'resource="memory"'
            f'}})'
        )
        return self._query(query)

    def get_replica_count(
        self, namespace: str, deployment: str
    ) -> Optional[float]:
        """Get current number of ready replicas."""
        query = (
            f'kube_deployment_status_replicas_ready{{'
            f'namespace="{namespace}", '
            f'deployment="{deployment}"'
            f'}}'
        )
        return self._query(query)

    # ── Historical Data (for ML training) ────────────────────────────

    def get_request_rate_history(
        self, job: str, start: str, end: str, step: str = "60s"
    ) -> list:
        """Get historical request rate time-series."""
        query = f'sum(rate(app_request_total{{job="{job}"}}[5m]))'
        return self._query_range(query, start, end, step)

    def get_cpu_history(
        self, namespace: str, deployment: str, start: str, end: str, step: str = "60s"
    ) -> list:
        """Get historical CPU utilization time-series."""
        query = (
            f'100 * avg(rate(container_cpu_usage_seconds_total{{'
            f'namespace="{namespace}", pod=~"{deployment}-.*", '
            f'container!="POD", container!=""}}[5m]))'
        )
        return self._query_range(query, start, end, step)
