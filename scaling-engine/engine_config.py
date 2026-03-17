"""
Configuration — Scaling Engine settings.
"""

import os
from dataclasses import dataclass


@dataclass
class EngineConfig:
    """Configuration for the Scaling Engine."""

    # API server (FastAPI backend)
    api_server_url: str = "http://api-server-service.autoscaler:8000"

    # Target workload
    namespace: str = "autoscaler"
    target_deployment: str = "target-app"
    hpa_name: str = "target-app-hpa"

    # Control loop
    loop_interval: int = 60  # seconds
    prediction_horizon: int = 15  # minutes

    # Policy weights
    reactive_weight: float = 0.4
    predictive_weight: float = 0.6
    cooldown_seconds: int = 300  # 5 minutes

    # Cost
    cost_per_pod_hour: float = 0.05  # USD

    # SLA
    sla_latency_threshold_ms: float = 500.0
    sla_error_rate_threshold: float = 0.01

    # Safety
    dry_run: bool = True  # Start safe

    @classmethod
    def from_env(cls) -> "EngineConfig":
        return cls(
            api_server_url=os.getenv("API_SERVER_URL", cls.api_server_url),
            namespace=os.getenv("NAMESPACE", cls.namespace),
            target_deployment=os.getenv("TARGET_DEPLOYMENT", cls.target_deployment),
            hpa_name=os.getenv("HPA_NAME", cls.hpa_name),
            loop_interval=int(os.getenv("LOOP_INTERVAL", str(cls.loop_interval))),
            prediction_horizon=int(os.getenv("PREDICTION_HORIZON", str(cls.prediction_horizon))),
            reactive_weight=float(os.getenv("REACTIVE_WEIGHT", str(cls.reactive_weight))),
            predictive_weight=float(os.getenv("PREDICTIVE_WEIGHT", str(cls.predictive_weight))),
            cooldown_seconds=int(os.getenv("COOLDOWN_SECONDS", str(cls.cooldown_seconds))),
            cost_per_pod_hour=float(os.getenv("COST_PER_POD_HOUR", str(cls.cost_per_pod_hour))),
            sla_latency_threshold_ms=float(os.getenv("SLA_LATENCY_THRESHOLD_MS", str(cls.sla_latency_threshold_ms))),
            sla_error_rate_threshold=float(os.getenv("SLA_ERROR_RATE_THRESHOLD", str(cls.sla_error_rate_threshold))),
            dry_run=os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes"),
        )
