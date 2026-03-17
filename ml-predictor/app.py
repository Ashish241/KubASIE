"""
FastAPI Microservice — Exposes ML predictions over HTTP.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from predict import PredictionService
from train import train_prophet, train_lstm
from preprocess import DataPreprocessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml-predictor-service")

# Global instances (load models on startup)
predictors = {
    "prophet": None,
    "lstm": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ML models...")
    try:
        predictors["prophet"] = PredictionService(model_type="prophet")
    except Exception as e:
        logger.error("Failed to load Prophet model: %s. Service will start without it.", e)
    try:
        predictors["lstm"] = PredictionService(model_type="lstm")
    except Exception as e:
        logger.error("Failed to load LSTM model: %s. Service will start without it.", e)
    
    if predictors["prophet"] and not predictors["prophet"].is_ready():
        logger.warning("Prophet model not found. Needs training.")
    if predictors["lstm"] and not predictors["lstm"].is_ready():
        logger.warning("LSTM model not found. Needs training.")
        
    yield
    logger.info("Shutting down ML Predictor Service...")


app = FastAPI(title="ML Predictor API", lifespan=lifespan)


class PredictRequest(BaseModel):
    horizon_minutes: int = 15


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "prophet_ready": predictors["prophet"].is_ready() if predictors.get("prophet") is not None else False,
        "lstm_ready": predictors["lstm"].is_ready() if predictors.get("lstm") is not None else False
    }


@app.get("/predict/{model_name}")
def predict_traffic(model_name: str, horizon: int = 15):
    """Generate traffic predictions using the requested model."""
    if model_name not in predictors:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not supported.")
        
    predictor = predictors[model_name]
    if predictor is None or not predictor.is_ready():
        raise HTTPException(
            status_code=503, 
            detail=f"{model_name} model is not trained yet. Run train.py first."
        )

    # For now, Prophet can predict purely based on time. 
    # LSTM requires recent data sequence, which we can fetch from Influx if needed.
    if model_name == "prophet":
        result = predictor.predict(horizon=horizon)
        if result is None:
            raise HTTPException(status_code=500, detail="Prediction failed.")
        return result
    else:
        # Placeholder for LSTM: requires passing actual data to `predict_from_data`
        raise HTTPException(
            status_code=501, 
            detail="LSTM prediction via HTTP requires passing recent sequence data. Not fully implemented."
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
