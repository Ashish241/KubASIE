"""
Tests for prediction service.
"""

from unittest.mock import patch, MagicMock

from predict import PredictionService


class TestPredictionService:

    def test_is_ready_no_model(self):
        with patch.object(PredictionService, "_load_model"):
            service = PredictionService.__new__(PredictionService)
            service.model = None
            assert service.is_ready() is False

    def test_is_ready_with_model(self):
        with patch.object(PredictionService, "_load_model"):
            service = PredictionService.__new__(PredictionService)
            service.model = MagicMock()
            assert service.is_ready() is True

    def test_predict_no_model_returns_none(self):
        with patch.object(PredictionService, "_load_model"):
            service = PredictionService.__new__(PredictionService)
            service.model = None
            service.model_type = "prophet"
            result = service.predict(horizon=15)
            assert result is None
