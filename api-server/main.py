"""
FastAPI REST API Server — Kubernetes Auto-Scaling Intelligence Engine

Exposes endpoints for predictions, metrics, scaling controls,
cost analysis, and SLA monitoring.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api-server")

# ── Pydantic Schemas ─────────────────────────────────────────────────

class PredictionResponse(BaseModel):
    model: str
    horizon_minutes: int
    predictions: list

class MetricsResponse(BaseModel):
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    request_rate: float = 0.0
    latency_p50: float = 0.0
    latency_p99: float = 0.0
    replica_count: int = 0
    timestamp: str = ""

class ScalingEvent(BaseModel):
    timestamp: str
    action: str
    target_replicas: int
    reason: str

class CostSummary(BaseModel):
    total_savings_usd: float = 0.0
    avg_replicas: float = 0.0
    avg_max_replicas: float = 0.0
    efficiency_percent: float = 0.0

class SLAStatus(BaseModel):
    status: str = "unknown"
    compliance_percent: float = 0.0
    total_violations: int = 0

class SettingsUpdate(BaseModel):
    sla_latency_threshold_ms: Optional[float] = None
    sla_error_rate_threshold: Optional[float] = None
    reactive_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    predictive_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    cooldown_seconds: Optional[int] = Field(None, ge=0)

class ScalingOverride(BaseModel):
    replicas: int = Field(..., ge=1, le=20)
    reason: str = "Manual override"

# ML Predictor Service URL
ML_PREDICTOR_URL = os.environ.get("ML_PREDICTOR_URL", "http://localhost:8001")


# ── In-memory state (in production, this would connect to the real services) ──
app_state = {
    "metrics": {
        "cpu_utilization": 45.2,
        "memory_utilization": 38.7,
        "request_rate": 67.5,
        "latency_p50": 0.032,
        "latency_p99": 0.142,
        "replica_count": 3,
    },
    "scaling_history": [],
    "settings": {
        "sla_latency_threshold_ms": 500.0,
        "sla_error_rate_threshold": 0.01,
        "reactive_weight": 0.4,
        "predictive_weight": 0.6,
        "cooldown_seconds": 300,
    },
}


# ── App Lifecycle ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 API Server starting...")
    yield
    logger.info("API Server shutting down.")


app = FastAPI(
    title="K8s Auto-Scaling Intelligence Engine API",
    description="REST API for the Kubernetes Auto-Scaling Intelligence Engine. "
                "Provides endpoints for traffic predictions, metrics, scaling controls, "
                "cost analysis, and SLA monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Prediction Endpoints ────────────────────────────────────────────

@app.get("/api/predictions", response_model=PredictionResponse, tags=["Predictions"])
async def get_predictions(horizon: int = Query(15, ge=5, le=120), model: str = Query("prophet")):
    """Get traffic predictions for the next N minutes from the ML Predictor microservice."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{ML_PREDICTOR_URL}/predict/{model}"
            response = await client.get(url, params={"horizon": horizon}, timeout=10.0)
            
            if response.status_code != 200:
                logger.error("ML service returned error %d: %s", response.status_code, response.text)
                raise HTTPException(status_code=502, detail=f"ML Predictor Error: {response.text}")
                
            data = response.json()
            return PredictionResponse(
                model=data.get("model", model),
                horizon_minutes=data.get("horizon_minutes", horizon),
                predictions=data.get("predictions", [])
            )
            
    except httpx.RequestError as e:
        logger.error("Connection error to ML service: %s", e)
        raise HTTPException(status_code=503, detail="ML Predictor service is unreachable")
    except Exception as e:
        logger.error("Prediction failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Metrics Endpoints ────────────────────────────────────────────────

@app.get("/api/metrics/current", tags=["Metrics"])
async def get_current_metrics():
    """Get current cluster and application metrics."""
    return {
        **app_state["metrics"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/metrics/history", tags=["Metrics"])
async def get_metrics_history(
    field: str = Query("request_rate"),
    start: str = Query("-1h"),
    window: str = Query("1m"),
):
    """Get historical metrics from InfluxDB."""
    # In production, this queries InfluxDB
    import math
    data = []
    for i in range(60):
        data.append({
            "time": f"2025-01-01T00:{i:02d}:00Z",
            "value": round(50 + 30 * math.sin(i * 0.1) + (i % 10) * 2, 2),
        })
    return {"field": field, "start": start, "window": window, "data": data}


# ── Scaling Endpoints ────────────────────────────────────────────────

@app.get("/api/scaling/history", tags=["Scaling"])
async def get_scaling_history():
    """Get history of scaling decisions."""
    return {"events": app_state["scaling_history"][-50:]}


@app.get("/api/scaling/status", tags=["Scaling"])
async def get_scaling_status():
    """Get current HPA and deployment status."""
    return {
        "hpa": {
            "name": "target-app-hpa",
            "min_replicas": 1,
            "max_replicas": 10,
            "current_replicas": app_state["metrics"]["replica_count"],
            "target_cpu_percent": 50,
        },
        "deployment": {
            "name": "target-app",
            "ready_replicas": app_state["metrics"]["replica_count"],
            "available_replicas": app_state["metrics"]["replica_count"],
        },
    }


@app.post("/api/scaling/override", tags=["Scaling"])
async def scaling_override(override: ScalingOverride):
    """Manually override the scaling target."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "manual_override",
        "target_replicas": override.replicas,
        "reason": override.reason,
    }
    app_state["scaling_history"].append(event)
    app_state["metrics"]["replica_count"] = override.replicas
    logger.info("Manual scaling override: %d replicas (%s)", override.replicas, override.reason)
    return {"status": "applied", "event": event}


# ── Cost Endpoints ───────────────────────────────────────────────────

@app.get("/api/cost/summary", tags=["Cost"])
async def get_cost_summary():
    """Get cost savings summary."""
    return {
        "total_savings_usd": 12.45,
        "avg_replicas": 3.2,
        "avg_max_replicas": 10.0,
        "efficiency_percent": 68.0,
        "cost_per_pod_hour": 0.05,
        "period": "last 24 hours",
    }


@app.get("/api/cost/hourly", tags=["Cost"])
async def get_cost_hourly():
    """Get hourly cost breakdown."""
    return {
        "hours": [
            {"hour": f"2025-01-01T{h:02d}", "savings_usd": round(0.5 + h * 0.02, 2), "avg_pods": 3}
            for h in range(24)
        ]
    }


# ── SLA Endpoints ────────────────────────────────────────────────────

@app.get("/api/sla/status", tags=["SLA"])
async def get_sla_status():
    """Get SLA compliance status."""
    return {
        "status": "healthy",
        "compliance_percent": 99.85,
        "recent_compliance_percent": 100.0,
        "total_checks": 1440,
        "total_violations": 2,
        "thresholds": app_state["settings"],
    }


@app.get("/api/sla/trend", tags=["SLA"])
async def get_sla_trend():
    """Get SLA compliance trend."""
    return {
        "trend": "stable",
        "avg_latency_ms": 42.5,
        "p99_latency_ms": 142.0,
        "avg_error_rate": 0.001,
    }


# ── Settings Endpoints ──────────────────────────────────────────────

@app.get("/api/settings", tags=["Settings"])
async def get_settings():
    """Get current engine settings."""
    return app_state["settings"]


@app.put("/api/settings", tags=["Settings"])
async def update_settings(settings: SettingsUpdate):
    """Update engine settings (SLA thresholds, policy weights)."""
    updates = settings.model_dump(exclude_none=True)
    app_state["settings"].update(updates)
    logger.info("Settings updated: %s", updates)
    return {"status": "updated", "settings": app_state["settings"]}


# ── Health ───────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "service": "api-server"}


# ── Entry Point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
