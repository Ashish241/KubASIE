"""
Tests for Prometheus Query Client.
"""

import pytest
from unittest.mock import patch, MagicMock

from prometheus_query import PrometheusQuerier


@pytest.fixture
def querier():
    return PrometheusQuerier("http://localhost:9090")


def _mock_prom_response(value=42.0, status="success"):
    """Helper to build a mock Prometheus API response."""
    return {
        "status": status,
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {}, "value": [1609459200, str(value)]}
            ] if status == "success" else [],
        },
    }


class TestPrometheusQuerier:

    @patch("prometheus_query.requests.get")
    def test_get_request_rate(self, mock_get, querier):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_prom_response(25.5)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = querier.get_request_rate(job="target-app", window="5m")
        assert result == 25.5

        # Verify the PromQL query was correctly constructed
        call_args = mock_get.call_args
        assert "rate(app_request_total" in call_args[1]["params"]["query"]

    @patch("prometheus_query.requests.get")
    def test_get_cpu_utilization(self, mock_get, querier):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_prom_response(72.3)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = querier.get_cpu_utilization(namespace="autoscaler", deployment="target-app")
        assert result == 72.3

    @patch("prometheus_query.requests.get")
    def test_get_latency_percentile(self, mock_get, querier):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_prom_response(0.125)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = querier.get_latency_percentile(job="target-app", quantile=0.99)
        assert result == 0.125

    @patch("prometheus_query.requests.get")
    def test_empty_result(self, mock_get, querier):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = querier.get_request_rate(job="nonexistent")
        assert result == 0.0

    @patch("prometheus_query.requests.get")
    def test_connection_error(self, mock_get, querier):
        mock_get.side_effect = Exception("Connection refused")
        result = querier.get_request_rate(job="target-app")
        assert result is None
