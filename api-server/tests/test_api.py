"""
API Server Tests — Test all endpoints using httpx.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport, Response
from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_predictions(client):
    """Predictions endpoint proxies to ml-predictor; mock the outbound HTTP call."""
    mock_payload = {
        "model": "prophet",
        "horizon_minutes": 15,
        "predictions": [
            {"timestamp": f"2026-01-01T00:{i:02d}:00", "predicted_request_rate": 50.0 + i}
            for i in range(15)
        ],
    }
    mock_response = Response(200, json=mock_payload)

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("main.httpx.AsyncClient", return_value=mock_client_instance):
        resp = await client.get("/api/predictions?horizon=15")

    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "prophet"
    assert len(data["predictions"]) == 15


@pytest.mark.asyncio
async def test_get_current_metrics(client):
    resp = await client.get("/api/metrics/current")
    assert resp.status_code == 200
    data = resp.json()
    assert "cpu_utilization" in data
    assert "request_rate" in data


@pytest.mark.asyncio
async def test_get_scaling_status(client):
    resp = await client.get("/api/scaling/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "hpa" in data
    assert "deployment" in data


@pytest.mark.asyncio
async def test_scaling_override(client):
    resp = await client.post(
        "/api/scaling/override",
        json={"replicas": 5, "reason": "Test override"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


@pytest.mark.asyncio
async def test_cost_summary(client):
    resp = await client.get("/api/cost/summary")
    assert resp.status_code == 200
    assert "total_savings_usd" in resp.json()


@pytest.mark.asyncio
async def test_sla_status(client):
    resp = await client.get("/api/sla/status")
    assert resp.status_code == 200
    assert "compliance_percent" in resp.json()


@pytest.mark.asyncio
async def test_get_settings(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_settings(client):
    resp = await client.put(
        "/api/settings",
        json={"sla_latency_threshold_ms": 300.0, "reactive_weight": 0.5},
    )
    assert resp.status_code == 200
    assert resp.json()["settings"]["sla_latency_threshold_ms"] == 300.0


@pytest.mark.asyncio
async def test_swagger_docs(client):
    resp = await client.get("/docs")
    assert resp.status_code == 200
