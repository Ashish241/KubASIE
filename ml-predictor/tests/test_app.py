"""
Tests for ML Predictor FastAPI endpoints.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_predictors():
    """Patch predictor instances used by the FastAPI app."""
    prophet = MagicMock()
    prophet.is_ready.return_value = True
    prophet.predict.return_value = {
        "model": "prophet",
        "horizon_minutes": 15,
        "predictions": [
            {
                "timestamp": f"2026-01-01T00:{i:02d}:00",
                "predicted_request_rate": 50.0 + i,
                "lower_bound": 40.0 + i,
                "upper_bound": 60.0 + i,
            }
            for i in range(15)
        ],
    }

    lstm = MagicMock()
    lstm.is_ready.return_value = False

    return {"prophet": prophet, "lstm": lstm}


@pytest_asyncio.fixture
async def client(mock_predictors):
    """Create test client with mocked predictors."""
    with patch("app.PredictionService") as mock_svc:
        mock_svc.side_effect = lambda model_type: mock_predictors[model_type]

        # Import app AFTER patching so lifespan uses mocks
        from app import app, predictors
        predictors["prophet"] = mock_predictors["prophet"]
        predictors["lstm"] = mock_predictors["lstm"]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_health(client, mock_predictors):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["prophet_ready"] is True
    assert data["lstm_ready"] is False


@pytest.mark.asyncio
async def test_predict_prophet(client):
    resp = await client.get("/predict/prophet?horizon=15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "prophet"
    assert len(data["predictions"]) == 15


@pytest.mark.asyncio
async def test_predict_unknown_model_returns_404(client):
    resp = await client.get("/predict/xgboost")
    assert resp.status_code == 404
    assert "not supported" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_predict_lstm_not_implemented(client, mock_predictors):
    # LSTM is not ready
    resp = await client.get("/predict/lstm")
    assert resp.status_code == 503
    assert "not trained" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_predict_prophet_not_ready(client, mock_predictors):
    """When prophet model is not ready, expect 503."""
    mock_predictors["prophet"].is_ready.return_value = False
    resp = await client.get("/predict/prophet")
    assert resp.status_code == 503
    # Restore
    mock_predictors["prophet"].is_ready.return_value = True
