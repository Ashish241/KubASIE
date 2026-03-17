"""
Tests for Metrics Collector.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from collector import MetricsCollector
from config import Config


@pytest.fixture
def mock_config():
    return Config(
        prometheus_url="http://localhost:9090",
        influxdb_url="http://localhost:8086",
        influxdb_token="test-token",
        influxdb_org="test-org",
        influxdb_bucket="test-bucket",
        namespace="test",
        target_deployment="test-app",
        target_job="test-app",
        collection_interval=5,
    )


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    @patch("collector.InfluxWriter")
    @patch("collector.PrometheusQuerier")
    def test_collect_once_success(self, MockProm, MockInflux, mock_config):
        """Test successful metric collection."""
        mock_prom = MockProm.return_value
        mock_prom.get_request_rate.return_value = 42.5
        mock_prom.get_latency_percentile.side_effect = [0.05, 0.25]
        mock_prom.get_cpu_utilization.return_value = 65.3
        mock_prom.get_memory_utilization.return_value = 40.1
        mock_prom.get_replica_count.return_value = 3.0

        collector = MetricsCollector(mock_config)
        metrics = collector.collect_once()

        assert metrics["request_rate"] == 42.5
        assert metrics["cpu_utilization"] == 65.3
        assert metrics["memory_utilization"] == 40.1
        assert metrics["replica_count"] == 3.0
        assert metrics["latency_p50"] == 0.05
        assert metrics["latency_p99"] == 0.25

        # Verify InfluxDB write was called
        collector.influx.write_metrics.assert_called_once()

    @patch("collector.InfluxWriter")
    @patch("collector.PrometheusQuerier")
    def test_collect_once_prometheus_failure(self, MockProm, MockInflux, mock_config):
        """Test graceful handling of Prometheus errors."""
        mock_prom = MockProm.return_value
        mock_prom.get_request_rate.side_effect = Exception("Connection refused")

        collector = MetricsCollector(mock_config)
        # Should not raise
        metrics = collector.collect_once()
        assert isinstance(metrics, dict)

    @patch("collector.InfluxWriter")
    @patch("collector.PrometheusQuerier")
    def test_shutdown_signal(self, MockProm, MockInflux, mock_config):
        """Test graceful shutdown."""
        collector = MetricsCollector(mock_config)
        assert collector._running is True

        collector._handle_shutdown(None, None)
        assert collector._running is False


class TestConfig:
    """Test configuration loading."""

    def test_default_config(self):
        config = Config()
        assert config.collection_interval == 30
        assert config.namespace == "autoscaler"

    @patch.dict("os.environ", {"COLLECTION_INTERVAL": "10", "NAMESPACE": "prod"})
    def test_config_from_env(self):
        config = Config.from_env()
        assert config.collection_interval == 10
        assert config.namespace == "prod"
