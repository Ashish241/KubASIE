"""
Scaling Policies — Reactive, predictive, and hybrid scaling strategies.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger("scaling-engine.policies")


@dataclass
class ScalingDecision:
    """Represents a scaling action decided by a policy."""
    action: str  # "scale_up", "scale_down", "no_change"
    target_replicas: int
    target_cpu_percent: int = 50
    reason: str = ""
    confidence: float = 0.0
    policy: str = ""


class ReactivePolicy:
    """
    Rule-based scaling based on current metrics thresholds.

    Simple but reliable — acts on what's happening NOW.
    """

    def __init__(
        self,
        cpu_scale_up_threshold: float = 70.0,
        cpu_scale_down_threshold: float = 30.0,
        memory_scale_up_threshold: float = 80.0,
        request_rate_per_pod: float = 50.0,
    ):
        self.cpu_up = cpu_scale_up_threshold
        self.cpu_down = cpu_scale_down_threshold
        self.mem_up = memory_scale_up_threshold
        self.rps_per_pod = request_rate_per_pod

    def decide(
        self,
        current_metrics: Dict,
        current_replicas: int,
        min_replicas: int,
        max_replicas: int,
    ) -> ScalingDecision:
        """Decide scaling action based on current metrics."""
        cpu = current_metrics.get("cpu_utilization", 0)
        mem = current_metrics.get("memory_utilization", 0)
        rps = current_metrics.get("request_rate", 0)

        # CPU-based scaling
        if cpu > self.cpu_up:
            target = min(current_replicas + 1, max_replicas)
            return ScalingDecision(
                action="scale_up",
                target_replicas=target,
                reason=f"CPU at {cpu:.1f}% (threshold: {self.cpu_up}%)",
                confidence=min(1.0, cpu / 100),
                policy="reactive",
            )

        # Memory-based scaling
        if mem > self.mem_up:
            target = min(current_replicas + 1, max_replicas)
            return ScalingDecision(
                action="scale_up",
                target_replicas=target,
                reason=f"Memory at {mem:.1f}% (threshold: {self.mem_up}%)",
                confidence=min(1.0, mem / 100),
                policy="reactive",
            )

        # Request rate based scaling
        if rps > 0 and self.rps_per_pod > 0:
            desired = max(1, int(rps / self.rps_per_pod) + 1)
            if desired > current_replicas:
                target = min(desired, max_replicas)
                return ScalingDecision(
                    action="scale_up",
                    target_replicas=target,
                    reason=f"RPS={rps:.1f} needs ~{desired} pods ({self.rps_per_pod} rps/pod)",
                    confidence=0.7,
                    policy="reactive",
                )

        # Scale down if underutilized
        if cpu < self.cpu_down and mem < self.cpu_down and current_replicas > min_replicas:
            target = max(current_replicas - 1, min_replicas)
            return ScalingDecision(
                action="scale_down",
                target_replicas=target,
                reason=f"Low utilization: CPU={cpu:.1f}%, MEM={mem:.1f}%",
                confidence=0.6,
                policy="reactive",
            )

        return ScalingDecision(
            action="no_change",
            target_replicas=current_replicas,
            reason="Metrics within normal range",
            policy="reactive",
        )


class PredictivePolicy:
    """
    ML-driven scaling based on traffic predictions.

    Proactive — scales BEFORE traffic arrives.
    """

    def __init__(
        self,
        request_rate_per_pod: float = 50.0,
        scale_up_buffer: float = 1.2,  # 20% buffer above predicted need
    ):
        self.rps_per_pod = request_rate_per_pod
        self.buffer = scale_up_buffer

    def decide(
        self,
        predictions: Optional[Dict],
        current_replicas: int,
        min_replicas: int,
        max_replicas: int,
    ) -> ScalingDecision:
        """Decide scaling based on predicted traffic."""
        if predictions is None or "predictions" not in predictions:
            return ScalingDecision(
                action="no_change",
                target_replicas=current_replicas,
                reason="No predictions available",
                policy="predictive",
            )

        pred_list = predictions["predictions"]
        if not pred_list:
            return ScalingDecision(
                action="no_change",
                target_replicas=current_replicas,
                reason="Empty predictions",
                policy="predictive",
            )

        # Find peak predicted request rate
        peak_rps = max(
            p.get("predicted_request_rate", 0)
            for p in pred_list
        )

        # Calculate desired replicas with buffer
        desired = max(1, int((peak_rps / self.rps_per_pod) * self.buffer) + 1)
        desired = min(desired, max_replicas)
        desired = max(desired, min_replicas)

        if desired > current_replicas:
            return ScalingDecision(
                action="scale_up",
                target_replicas=desired,
                reason=f"Predicted peak RPS={peak_rps:.1f} → need {desired} pods (buffer={self.buffer}x)",
                confidence=0.8,
                policy="predictive",
            )
        elif desired < current_replicas - 1:
            # Conservative scale-down (only if significantly over-provisioned)
            return ScalingDecision(
                action="scale_down",
                target_replicas=desired,
                reason=f"Predicted peak RPS={peak_rps:.1f} → only need {desired} pods",
                confidence=0.6,
                policy="predictive",
            )

        return ScalingDecision(
            action="no_change",
            target_replicas=current_replicas,
            reason=f"Current replicas adequate for predicted peak RPS={peak_rps:.1f}",
            policy="predictive",
        )


class HybridPolicy:
    """
    Combines reactive + predictive policies with configurable weights.

    This is the recommended policy for production — it reacts to current
    conditions AND prepares for predicted traffic.
    """

    def __init__(self, config=None):
        reactive_weight = getattr(config, "reactive_weight", 0.4)
        predictive_weight = getattr(config, "predictive_weight", 0.6)

        self.reactive = ReactivePolicy()
        self.predictive = PredictivePolicy()
        self.reactive_weight = reactive_weight
        self.predictive_weight = predictive_weight
        self._last_scale_time: Optional[datetime] = None
        self._cooldown_seconds = getattr(config, "cooldown_seconds", 300)

    def decide(
        self,
        current_metrics: Dict,
        predictions: Optional[Dict],
        current_replicas: int,
        min_replicas: int,
        max_replicas: int,
    ) -> ScalingDecision:
        """Combined decision from reactive + predictive policies."""
        now = datetime.now(timezone.utc)

        # Get decisions from both policies
        reactive_decision = self.reactive.decide(
            current_metrics, current_replicas, min_replicas, max_replicas
        )
        predictive_decision = self.predictive.decide(
            predictions, current_replicas, min_replicas, max_replicas
        )

        # Weighted combination of target replicas
        weighted_target = (
            self.reactive_weight * reactive_decision.target_replicas
            + self.predictive_weight * predictive_decision.target_replicas
        )
        target = int(round(weighted_target))
        target = max(min_replicas, min(target, max_replicas))

        # Determine action
        if target > current_replicas:
            action = "scale_up"
        elif target < current_replicas:
            action = "scale_down"
        else:
            action = "no_change"

        # Enforce cooldown for scale-down (prevent flapping)
        if action == "scale_down" and self._last_scale_time:
            elapsed = (now - self._last_scale_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                return ScalingDecision(
                    action="no_change",
                    target_replicas=current_replicas,
                    reason=f"Cooldown active ({elapsed:.0f}s / {self._cooldown_seconds}s)",
                    policy="hybrid",
                )

        if action != "no_change":
            self._last_scale_time = now

        reason = (
            f"Hybrid: reactive={reactive_decision.target_replicas} "
            f"({reactive_decision.reason}), "
            f"predictive={predictive_decision.target_replicas} "
            f"({predictive_decision.reason})"
        )

        return ScalingDecision(
            action=action,
            target_replicas=target,
            reason=reason,
            confidence=max(reactive_decision.confidence, predictive_decision.confidence),
            policy="hybrid",
        )
