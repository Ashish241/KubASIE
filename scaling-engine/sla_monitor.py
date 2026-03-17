"""
SLA Monitor — Tracks service level agreement compliance.
"""

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("scaling-engine.sla")


class SLAMonitor:
    """
    Monitors SLA compliance by tracking latency and error rates.

    Alerts when SLA thresholds are breached and calculates
    uptime/compliance percentages.
    """

    def __init__(
        self,
        latency_threshold_ms: float = 500.0,
        error_rate_threshold: float = 0.01,  # 1%
    ):
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.records: List[Dict] = []
        self.violations: List[Dict] = []

    def record(
        self,
        timestamp: datetime,
        latency_p99_ms: float,
        error_rate: float = 0.0,
    ):
        """Record an SLA data point."""
        is_violation = (
            latency_p99_ms > self.latency_threshold_ms
            or error_rate > self.error_rate_threshold
        )

        entry = {
            "timestamp": timestamp.isoformat(),
            "latency_p99_ms": round(latency_p99_ms, 2),
            "error_rate": round(error_rate, 4),
            "is_violation": is_violation,
        }
        self.records.append(entry)

        if is_violation:
            reasons = []
            if latency_p99_ms > self.latency_threshold_ms:
                reasons.append(
                    f"Latency p99={latency_p99_ms:.1f}ms > {self.latency_threshold_ms}ms"
                )
            if error_rate > self.error_rate_threshold:
                reasons.append(
                    f"Error rate={error_rate:.2%} > {self.error_rate_threshold:.2%}"
                )

            violation = {
                "timestamp": timestamp.isoformat(),
                "reasons": reasons,
                "latency_p99_ms": round(latency_p99_ms, 2),
                "error_rate": round(error_rate, 4),
            }
            self.violations.append(violation)
            logger.warning("⚠️  SLA VIOLATION: %s", " | ".join(reasons))

        # Keep history bounded
        if len(self.records) > 10000:
            self.records = self.records[-10000:]
        if len(self.violations) > 1000:
            self.violations = self.violations[-1000:]

    def get_status(self) -> Dict:
        """Get current SLA compliance status."""
        if not self.records:
            return {
                "status": "unknown",
                "compliance_percent": 0.0,
                "total_checks": 0,
                "total_violations": 0,
                "thresholds": {
                    "latency_p99_ms": self.latency_threshold_ms,
                    "error_rate": self.error_rate_threshold,
                },
            }

        total = len(self.records)
        violations = sum(1 for r in self.records if r["is_violation"])
        compliance = ((total - violations) / total) * 100

        # Determine status color
        if compliance >= 99.9:
            status = "healthy"
        elif compliance >= 99.0:
            status = "warning"
        else:
            status = "critical"

        # Recent trend (last 100 checks)
        recent = self.records[-100:]
        recent_violations = sum(1 for r in recent if r["is_violation"])
        recent_compliance = ((len(recent) - recent_violations) / len(recent)) * 100

        return {
            "status": status,
            "compliance_percent": round(compliance, 2),
            "recent_compliance_percent": round(recent_compliance, 2),
            "total_checks": total,
            "total_violations": violations,
            "recent_violations": self.violations[-5:],
            "thresholds": {
                "latency_p99_ms": self.latency_threshold_ms,
                "error_rate": self.error_rate_threshold,
            },
        }

    def get_trend(self, window: int = 100) -> Dict:
        """Get SLA trend over the last `window` data points."""
        if len(self.records) < 2:
            return {"trend": "insufficient_data"}

        recent = self.records[-window:]
        latencies = [r["latency_p99_ms"] for r in recent]
        error_rates = [r["error_rate"] for r in recent]

        import numpy as np
        avg_latency = float(np.mean(latencies))
        p99_latency = float(np.percentile(latencies, 99))

        # Compare first half vs second half for trend
        mid = len(recent) // 2
        first_half_violations = sum(1 for r in recent[:mid] if r["is_violation"])
        second_half_violations = sum(1 for r in recent[mid:] if r["is_violation"])

        if second_half_violations > first_half_violations:
            trend = "degrading"
        elif second_half_violations < first_half_violations:
            trend = "improving"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "avg_latency_ms": round(avg_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "avg_error_rate": round(float(np.mean(error_rates)), 4),
            "data_points": len(recent),
        }
