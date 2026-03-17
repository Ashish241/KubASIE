"""
Cost Optimizer — Tracks infrastructure cost savings from intelligent scaling.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger("scaling-engine.cost")


class CostOptimizer:
    """
    Calculates and tracks cost savings from predictive auto-scaling.

    Compares actual pod usage against worst-case (always max replicas).
    """

    def __init__(self, cost_per_pod_hour: float = 0.05):
        """
        Args:
            cost_per_pod_hour: Estimated cost per pod per hour (USD).
        """
        self.cost_per_pod_hour = cost_per_pod_hour
        self.records: List[Dict] = []

    def record(
        self,
        timestamp: datetime,
        actual_replicas: int,
        max_possible_replicas: int,
    ):
        """Record a scaling snapshot for cost tracking."""
        saved_pods = max_possible_replicas - actual_replicas
        saved_cost = saved_pods * (self.cost_per_pod_hour / 60)  # per-minute rate

        self.records.append({
            "timestamp": timestamp.isoformat(),
            "actual_replicas": actual_replicas,
            "max_replicas": max_possible_replicas,
            "saved_pods": saved_pods,
            "saved_cost_usd": round(saved_cost, 4),
        })

        # Keep last 10,000 records
        if len(self.records) > 10000:
            self.records = self.records[-10000:]

    def get_summary(self) -> Dict:
        """Get cost savings summary."""
        if not self.records:
            return {
                "total_savings_usd": 0.0,
                "avg_replicas": 0,
                "avg_max_replicas": 0,
                "efficiency_percent": 0.0,
                "total_snapshots": 0,
            }

        total_savings = sum(r["saved_cost_usd"] for r in self.records)
        avg_replicas = sum(r["actual_replicas"] for r in self.records) / len(self.records)
        avg_max = sum(r["max_replicas"] for r in self.records) / len(self.records)

        # Efficiency: how many pods were we NOT running vs max
        efficiency = ((avg_max - avg_replicas) / avg_max * 100) if avg_max > 0 else 0

        return {
            "total_savings_usd": round(total_savings, 2),
            "avg_replicas": round(avg_replicas, 1),
            "avg_max_replicas": round(avg_max, 1),
            "efficiency_percent": round(efficiency, 1),
            "total_snapshots": len(self.records),
            "cost_per_pod_hour": self.cost_per_pod_hour,
        }

    def get_hourly_breakdown(self) -> List[Dict]:
        """Get cost savings broken down by hour."""
        from collections import defaultdict

        hourly = defaultdict(lambda: {"savings": 0.0, "avg_pods": [], "count": 0})

        for r in self.records:
            hour_key = r["timestamp"][:13]  # YYYY-MM-DDTHH
            hourly[hour_key]["savings"] += r["saved_cost_usd"]
            hourly[hour_key]["avg_pods"].append(r["actual_replicas"])
            hourly[hour_key]["count"] += 1

        return [
            {
                "hour": k,
                "savings_usd": round(v["savings"], 4),
                "avg_pods": round(sum(v["avg_pods"]) / len(v["avg_pods"]), 1),
                "snapshots": v["count"],
            }
            for k, v in sorted(hourly.items())
        ]

    def get_right_sizing_recommendation(self, cpu_history: List[float]) -> Dict:
        """
        Recommend resource requests based on actual usage.

        Args:
            cpu_history: List of CPU utilization percentages over time.
        """
        if not cpu_history:
            return {"recommendation": "Insufficient data"}

        import numpy as np
        p50 = float(np.percentile(cpu_history, 50))
        p90 = float(np.percentile(cpu_history, 90))
        p99 = float(np.percentile(cpu_history, 99))
        peak = float(np.max(cpu_history))

        # Recommend: request = p90, limit = p99 * 1.2
        return {
            "cpu_p50": round(p50, 1),
            "cpu_p90": round(p90, 1),
            "cpu_p99": round(p99, 1),
            "cpu_peak": round(peak, 1),
            "recommended_request_percent": round(p90, 0),
            "recommended_limit_percent": round(min(p99 * 1.2, 100), 0),
            "analysis": (
                f"CPU usage: p50={p50:.1f}%, p90={p90:.1f}%, peak={peak:.1f}%. "
                f"Recommend setting request at p90 ({p90:.0f}%) and limit at p99×1.2 ({min(p99 * 1.2, 100):.0f}%)."
            ),
        }
