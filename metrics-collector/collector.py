"""
Metrics Collector — Kubernetes Auto-Scaling Intelligence Engine

Periodically scrapes Prometheus for application & cluster metrics
and stores them in InfluxDB for historical analysis and ML training.
"""

import time
import logging
import signal
import sys
from datetime import datetime, timezone

from config import Config
from prometheus_query import PrometheusQuerier
from influx_writer import InfluxWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("metrics-collector")


class MetricsCollector:
    """Main collector loop that bridges Prometheus → InfluxDB."""

    def __init__(self, config: Config):
        self.config = config
        self.prometheus = PrometheusQuerier(config.prometheus_url)
        self.influx = InfluxWriter(
            url=config.influxdb_url,
            token=config.influxdb_token,
            org=config.influxdb_org,
            bucket=config.influxdb_bucket,
        )
        self._running = True

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received, stopping collector...")
        self._running = False

    def collect_once(self) -> dict:
        """Collect all metrics once and return them as a dict."""
        now = datetime.now(timezone.utc)
        metrics = {}

        try:
            # ── Application metrics ──────────────────────────────────
            metrics["request_rate"] = self.prometheus.get_request_rate(
                job=self.config.target_job,
                window=self.config.rate_window,
            )
            metrics["latency_p50"] = self.prometheus.get_latency_percentile(
                job=self.config.target_job, quantile=0.5,
            )
            metrics["latency_p99"] = self.prometheus.get_latency_percentile(
                job=self.config.target_job, quantile=0.99,
            )

            # ── Cluster resource metrics ─────────────────────────────
            metrics["cpu_utilization"] = self.prometheus.get_cpu_utilization(
                namespace=self.config.namespace,
                deployment=self.config.target_deployment,
            )
            metrics["memory_utilization"] = self.prometheus.get_memory_utilization(
                namespace=self.config.namespace,
                deployment=self.config.target_deployment,
            )

            # ── Pod count ────────────────────────────────────────────
            metrics["replica_count"] = self.prometheus.get_replica_count(
                namespace=self.config.namespace,
                deployment=self.config.target_deployment,
            )

            logger.info(
                "Collected metrics: req_rate=%.2f cpu=%.1f%% mem=%.1f%% p99=%.3fs replicas=%d",
                metrics.get("request_rate", 0),
                metrics.get("cpu_utilization", 0),
                metrics.get("memory_utilization", 0),
                metrics.get("latency_p99", 0),
                metrics.get("replica_count", 0),
            )

            # ── Write to InfluxDB ────────────────────────────────────
            self.influx.write_metrics(
                measurement="app_metrics",
                tags={
                    "namespace": self.config.namespace,
                    "deployment": self.config.target_deployment,
                },
                fields=metrics,
                timestamp=now,
            )

        except Exception as e:
            logger.error("Failed to collect metrics: %s", e, exc_info=True)

        return metrics

    def run(self):
        """Run the collection loop until shutdown."""
        logger.info(
            "Starting metrics collector (interval=%ds, prometheus=%s)",
            self.config.collection_interval,
            self.config.prometheus_url,
        )

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        while self._running:
            self.collect_once()
            time.sleep(self.config.collection_interval)

        self.influx.close()
        logger.info("Metrics collector stopped.")


def main():
    config = Config.from_env()
    collector = MetricsCollector(config)
    collector.run()


if __name__ == "__main__":
    main()
