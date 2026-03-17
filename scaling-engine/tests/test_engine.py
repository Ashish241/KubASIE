"""
Tests for Scaling Engine core loop.
"""

import pytest
from unittest.mock import patch, MagicMock

from engine import ScalingEngine
from engine_config import EngineConfig


@pytest.fixture
def engine():
    config = EngineConfig(
        api_server_url="http://localhost:8000",
        dry_run=True,
        loop_interval=5,
    )
    with patch("engine.K8sController"):
        with patch("engine.HybridPolicy"):
            eng = ScalingEngine(config)
            eng.k8s = MagicMock()
            eng.k8s.get_hpa_status.return_value = {
                "current_replicas": 2,
                "min_replicas": 1,
                "max_replicas": 10,
            }
            eng.k8s.patch_hpa.return_value = True
            return eng


class TestScalingEngine:

    @patch("engine.requests.get")
    def test_execute_once_success(self, mock_get, engine):
        """Test one scaling loop cycle."""
        # Mock metrics response
        mock_metrics_resp = MagicMock()
        mock_metrics_resp.json.return_value = {
            "cpu_utilization": 65.0,
            "memory_utilization": 40.0,
            "request_rate": 100.0,
            "latency_p99": 0.15,
        }
        mock_metrics_resp.raise_for_status = MagicMock()

        # Mock predictions response
        mock_pred_resp = MagicMock()
        mock_pred_resp.json.return_value = {
            "predictions": [{"predicted_request_rate": 120.0}]
        }
        mock_pred_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_metrics_resp, mock_pred_resp]

        from policies import ScalingDecision
        engine.policy.decide.return_value = ScalingDecision(
            action="scale_up",
            target_replicas=3,
            reason="Test scale up",
            policy="hybrid",
        )

        decision = engine.execute_once()
        assert decision is not None
        assert decision.action == "scale_up"
        assert len(engine.scaling_history) == 1

    def test_get_status(self, engine):
        status = engine.get_status()
        assert "running" in status
        assert "dry_run" in status
        assert "cost_summary" in status
        assert "sla_status" in status

    @patch("engine.requests.get")
    def test_handles_metrics_failure(self, mock_get, engine):
        mock_get.side_effect = Exception("Connection refused")
        decision = engine.execute_once()
        assert decision is None
