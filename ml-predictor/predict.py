"""
Prediction Server — loads trained model and serves predictions.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from model import ProphetPredictor, LSTMPredictor

logger = logging.getLogger("ml-predictor.predict")

MODELS_DIR = Path(__file__).parent / "models"


class PredictionService:
    """Loads trained models and serves traffic predictions."""

    def __init__(self, model_type: str = "prophet"):
        self.model_type = model_type
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the latest trained model."""
        if self.model_type == "prophet":
            model_path = MODELS_DIR / "prophet_latest.pkl"
            if model_path.exists():
                self.model = ProphetPredictor()
                self.model.load(str(model_path))
                logger.info("Loaded Prophet model from %s", model_path)
            else:
                logger.warning("No Prophet model found at %s", model_path)

        elif self.model_type == "lstm":
            model_path = MODELS_DIR / "lstm_latest.pt"
            if model_path.exists():
                self.model = LSTMPredictor()
                self.model.load(str(model_path))
                logger.info("Loaded LSTM model from %s", model_path)
            else:
                logger.warning("No LSTM model found at %s", model_path)

    def predict(self, horizon: int = 15) -> Optional[Dict]:
        """
        Generate traffic predictions.

        Args:
            horizon: Number of minutes to predict ahead.

        Returns:
            Dict with predictions, timestamps, and confidence intervals.
        """
        if self.model is None:
            logger.error("No model loaded — cannot predict.")
            return None

        try:
            if self.model_type == "prophet":
                forecast = self.model.predict(horizon=horizon)
                return {
                    "model": "prophet",
                    "horizon_minutes": horizon,
                    "predictions": [
                        {
                            "timestamp": row["ds"].isoformat(),
                            "predicted_request_rate": round(max(0, row["yhat"]), 2),
                            "lower_bound": round(max(0, row["yhat_lower"]), 2),
                            "upper_bound": round(max(0, row["yhat_upper"]), 2),
                        }
                        for _, row in forecast.iterrows()
                    ],
                }
            else:
                logger.warning("LSTM predict requires input sequence — use predict_from_data()")
                return None

        except Exception as e:
            logger.error("Prediction failed: %s", e, exc_info=True)
            return None

    def predict_from_data(self, recent_data: np.ndarray, horizon: int = 15) -> Optional[Dict]:
        """
        Predict using recent data as input (for LSTM).

        Args:
            recent_data: Recent metrics array of shape (sequence_length, n_features)
        """
        if self.model is None:
            return None

        try:
            if self.model_type == "lstm":
                predictions = self.model.predict_from_sequence(recent_data)
                return {
                    "model": "lstm",
                    "horizon_minutes": horizon,
                    "predictions": [
                        {"step": i + 1, "predicted_request_rate": round(float(v), 2)}
                        for i, v in enumerate(predictions)
                    ],
                }
            else:
                return self.predict(horizon=horizon)

        except Exception as e:
            logger.error("Prediction from data failed: %s", e, exc_info=True)
            return None

    def is_ready(self) -> bool:
        """Check if a model is loaded and ready to serve."""
        return self.model is not None

    def reload_model(self):
        """Reload the model (e.g., after retraining)."""
        logger.info("Reloading model...")
        self._load_model()
