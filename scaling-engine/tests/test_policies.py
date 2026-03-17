"""
Tests for Scaling Policies.
"""

import pytest

from policies import ReactivePolicy, PredictivePolicy, HybridPolicy


class TestReactivePolicy:

    def setup_method(self):
        self.policy = ReactivePolicy(
            cpu_scale_up_threshold=70.0,
            cpu_scale_down_threshold=30.0,
        )

    def test_scale_up_on_high_cpu(self):
        metrics = {"cpu_utilization": 85.0, "memory_utilization": 40.0, "request_rate": 20.0}
        decision = self.policy.decide(metrics, current_replicas=2, min_replicas=1, max_replicas=10)
        assert decision.action == "scale_up"
        assert decision.target_replicas == 3

    def test_scale_down_on_low_cpu(self):
        metrics = {"cpu_utilization": 15.0, "memory_utilization": 10.0, "request_rate": 5.0}
        decision = self.policy.decide(metrics, current_replicas=5, min_replicas=1, max_replicas=10)
        assert decision.action == "scale_down"
        assert decision.target_replicas == 4

    def test_no_change_normal_metrics(self):
        metrics = {"cpu_utilization": 50.0, "memory_utilization": 40.0, "request_rate": 20.0}
        decision = self.policy.decide(metrics, current_replicas=3, min_replicas=1, max_replicas=10)
        assert decision.action == "no_change"

    def test_respects_max_replicas(self):
        metrics = {"cpu_utilization": 95.0, "memory_utilization": 40.0, "request_rate": 20.0}
        decision = self.policy.decide(metrics, current_replicas=10, min_replicas=1, max_replicas=10)
        assert decision.target_replicas <= 10

    def test_respects_min_replicas(self):
        metrics = {"cpu_utilization": 5.0, "memory_utilization": 5.0, "request_rate": 1.0}
        decision = self.policy.decide(metrics, current_replicas=1, min_replicas=1, max_replicas=10)
        assert decision.action == "no_change"  # Already at min


class TestPredictivePolicy:

    def setup_method(self):
        self.policy = PredictivePolicy(request_rate_per_pod=50.0, scale_up_buffer=1.2)

    def test_scale_up_on_predicted_spike(self):
        predictions = {
            "predictions": [
                {"predicted_request_rate": 200.0},
                {"predicted_request_rate": 300.0},
                {"predicted_request_rate": 250.0},
            ]
        }
        decision = self.policy.decide(predictions, current_replicas=2, min_replicas=1, max_replicas=10)
        assert decision.action == "scale_up"
        assert decision.target_replicas > 2

    def test_no_change_when_adequate(self):
        predictions = {
            "predictions": [
                {"predicted_request_rate": 30.0},
                {"predicted_request_rate": 40.0},
            ]
        }
        decision = self.policy.decide(predictions, current_replicas=2, min_replicas=1, max_replicas=10)
        assert decision.action == "no_change"

    def test_handles_no_predictions(self):
        decision = self.policy.decide(None, current_replicas=3, min_replicas=1, max_replicas=10)
        assert decision.action == "no_change"
        assert decision.target_replicas == 3


class TestHybridPolicy:

    def test_combines_both_policies(self):
        from unittest.mock import MagicMock
        config = MagicMock()
        config.reactive_weight = 0.4
        config.predictive_weight = 0.6
        config.cooldown_seconds = 0  # Disable cooldown for tests

        policy = HybridPolicy(config)
        metrics = {"cpu_utilization": 80.0, "memory_utilization": 40.0, "request_rate": 30.0}
        predictions = {
            "predictions": [{"predicted_request_rate": 200.0}]
        }

        decision = policy.decide(
            metrics, predictions,
            current_replicas=2, min_replicas=1, max_replicas=10,
        )
        assert decision.policy == "hybrid"
        assert isinstance(decision.target_replicas, int)
