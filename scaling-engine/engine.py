"""
Scaling Engine — Core control loop for intelligent auto-scaling.
"""

import time
import logging
import signal
from datetime import datetime, timezone
from typing import Dict, Optional

import requests
from policies import HybridPolicy, ScalingDecision
from k8s_controller import K8sController
from cost_optimizer import CostOptimizer
from sla_monitor import SLAMonitor
from engine_config import EngineConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scaling-engine")


class ScalingEngine:
    """
    Main auto-scaling decision engine.

    Control loop:
    1. Fetch current metrics from the metrics API
    2. Fetch traffic predictions from the ML predictor API
    3. Run scaling policy to determine action
    4. Apply scaling decision to K8s HPA
    5. Log decision + update cost/SLA tracking
    """

    def __init__(self, config: EngineConfig):
        self.config = config
        self.policy = HybridPolicy(config)
        self.k8s = K8sController(
            namespace=config.namespace,
            deployment=config.target_deployment,
            hpa_name=config.hpa_name,
            dry_run=config.dry_run,
        )
        self.cost_optimizer = CostOptimizer(cost_per_pod_hour=config.cost_per_pod_hour)
        self.sla_monitor = SLAMonitor(
            latency_threshold_ms=config.sla_latency_threshold_ms,
            error_rate_threshold=config.sla_error_rate_threshold,
        )
        self._running = True
        self.scaling_history: list = []

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received.")
        self._running = False

    def fetch_current_metrics(self) -> Optional[Dict]:
        """Fetch current metrics from the metrics API."""
        try:
            resp = requests.get(
                f"{self.config.api_server_url}/api/metrics/current",
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to fetch current metrics: %s", e)
            return None

    def fetch_predictions(self, horizon: int = 15) -> Optional[Dict]:
        """Fetch traffic predictions from the ML predictor API."""
        try:
            resp = requests.get(
                f"{self.config.api_server_url}/api/predictions",
                params={"horizon": horizon},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to fetch predictions: %s", e)
            return None

    def execute_once(self) -> Optional[ScalingDecision]:
        """Execute one cycle of the scaling loop."""
        now = datetime.now(timezone.utc)

        # Step 1: Get current state
        metrics = self.fetch_current_metrics()
        if metrics is None:
            logger.warning("Skipping cycle — no metrics available")
            return None

        # Step 2: Get predictions
        predictions = self.fetch_predictions(horizon=self.config.prediction_horizon)

        # Step 3: Get current HPA state
        hpa_status = self.k8s.get_hpa_status()

        # Step 4: Run scaling policy
        decision = self.policy.decide(
            current_metrics=metrics,
            predictions=predictions,
            current_replicas=hpa_status.get("current_replicas", 1) if hpa_status else 1,
            min_replicas=hpa_status.get("min_replicas", 1) if hpa_status else 1,
            max_replicas=hpa_status.get("max_replicas", 10) if hpa_status else 10,
        )

        logger.info(
            "Scaling decision: action=%s, target_replicas=%d, reason=%s",
            decision.action, decision.target_replicas, decision.reason,
        )

        # Step 5: Apply if action needed
        if decision.action != "no_change":
            success = self.k8s.patch_hpa(
                min_replicas=max(1, decision.target_replicas - 1),
                max_replicas=max(decision.target_replicas + 2, 10),
                target_cpu=decision.target_cpu_percent,
            )
            if success:
                logger.info("✅ HPA patched: target_replicas=%d", decision.target_replicas)
            else:
                logger.error("❌ Failed to patch HPA")

        # Step 6: Track cost & SLA
        self.cost_optimizer.record(
            timestamp=now,
            actual_replicas=decision.target_replicas,
            max_possible_replicas=hpa_status.get("max_replicas", 10) if hpa_status else 10,
        )

        if metrics:
            self.sla_monitor.record(
                timestamp=now,
                latency_p99_ms=metrics.get("latency_p99", 0) * 1000,
                error_rate=metrics.get("error_rate", 0),
            )

        # Step 7: Log to history
        event = {
            "timestamp": now.isoformat(),
            "action": decision.action,
            "target_replicas": decision.target_replicas,
            "reason": decision.reason,
            "metrics": metrics,
            "prediction_available": predictions is not None,
        }
        self.scaling_history.append(event)

        # Keep only last 1000 events in memory
        if len(self.scaling_history) > 1000:
            self.scaling_history = self.scaling_history[-1000:]

        return decision

    def run(self):
        """Run the scaling engine control loop."""
        logger.info("🚀 Scaling Engine started (interval=%ds, dry_run=%s)",
                     self.config.loop_interval, self.config.dry_run)

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        while self._running:
            try:
                self.execute_once()
            except Exception as e:
                logger.error("Scaling loop error: %s", e, exc_info=True)

            time.sleep(self.config.loop_interval)

        logger.info("Scaling Engine stopped.")

    def get_status(self) -> Dict:
        """Get current engine status summary."""
        return {
            "running": self._running,
            "dry_run": self.config.dry_run,
            "loop_interval": self.config.loop_interval,
            "total_decisions": len(self.scaling_history),
            "recent_decisions": self.scaling_history[-10:],
            "cost_summary": self.cost_optimizer.get_summary(),
            "sla_status": self.sla_monitor.get_status(),
        }


def main():
    config = EngineConfig.from_env()
    engine = ScalingEngine(config)
    engine.run()


if __name__ == "__main__":
    main()
