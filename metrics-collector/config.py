"""
Configuration — Environment-based config for the Metrics Collector.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration loaded from environment variables with sensible defaults."""

    # Prometheus
    prometheus_url: str = "http://prometheus-service.autoscaler:9090"
    target_job: str = "target-app"
    rate_window: str = "5m"

    # InfluxDB
    influxdb_url: str = "http://influxdb-service.autoscaler:8086"
    influxdb_token: str = "autoscaler-token"
    influxdb_org: str = "autoscaler"
    influxdb_bucket: str = "metrics"

    # Target workload
    namespace: str = "autoscaler"
    target_deployment: str = "target-app"

    # Collection
    collection_interval: int = 30  # seconds

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            prometheus_url=os.getenv("PROMETHEUS_URL", cls.prometheus_url),
            target_job=os.getenv("TARGET_JOB", cls.target_job),
            rate_window=os.getenv("RATE_WINDOW", cls.rate_window),
            influxdb_url=os.getenv("INFLUXDB_URL", cls.influxdb_url),
            influxdb_token=os.getenv("INFLUXDB_TOKEN", cls.influxdb_token),
            influxdb_org=os.getenv("INFLUXDB_ORG", cls.influxdb_org),
            influxdb_bucket=os.getenv("INFLUXDB_BUCKET", cls.influxdb_bucket),
            namespace=os.getenv("NAMESPACE", cls.namespace),
            target_deployment=os.getenv("TARGET_DEPLOYMENT", cls.target_deployment),
            collection_interval=int(
                os.getenv("COLLECTION_INTERVAL", str(cls.collection_interval))
            ),
        )
