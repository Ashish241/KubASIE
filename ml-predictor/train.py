"""
Training Pipeline — End-to-end model training and evaluation.
"""

import os
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

from preprocess import DataPreprocessor
from model import ProphetPredictor, LSTMPredictor

# We need to import InfluxWriter from the metrics-collector module
import sys
collector_path = Path(__file__).parent.parent / "metrics-collector"
if collector_path.exists():
    sys.path.insert(0, str(collector_path))
try:
    from influx_writer import InfluxWriter
except ImportError:
    InfluxWriter = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ml-predictor.train")

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def train_prophet(
    df: pd.DataFrame,
    interval_width: float = 0.95,
    model_name: str = "prophet",
) -> Dict:
    """
    Train a Prophet model.

    Args:
        df: DataFrame with 'time' and 'value' columns (from InfluxDB or synthetic).
    """
    logger.info("═" * 60)
    logger.info("Training Prophet model")
    logger.info("═" * 60)

    # Prepare data in Prophet format (ds, y)
    prophet_df = df.rename(columns={"time": "ds", "value": "y"})[["ds", "y"]].copy()
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

    model = ProphetPredictor(interval_width=interval_width)
    metrics = model.train(prophet_df)

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODELS_DIR / f"{model_name}_{timestamp}.pkl"
    model.save(str(model_path))

    # Save latest symlink
    latest_path = MODELS_DIR / f"{model_name}_latest.pkl"
    model.save(str(latest_path))

    # Sample predictions
    predictions = model.predict(horizon=15)
    logger.info("Sample predictions (next 15 min):\n%s", predictions.to_string(index=False))

    # Save training report
    report = {
        "model": model_name,
        "timestamp": timestamp,
        "data_points": len(df),
        "metrics": metrics,
        "model_path": str(model_path),
    }
    report_path = MODELS_DIR / f"{model_name}_{timestamp}_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Training report saved to %s", report_path)
    return report


def train_lstm(
    df: pd.DataFrame,
    sequence_length: int = 60,
    forecast_horizon: int = 15,
    epochs: int = 50,
    model_name: str = "lstm",
) -> Dict:
    """
    Train an LSTM model.

    Args:
        df: DataFrame with 'time' and 'value' columns.
    """
    logger.info("═" * 60)
    logger.info("Training LSTM model")
    logger.info("═" * 60)

    # Preprocess
    preprocessor = DataPreprocessor(
        sequence_length=sequence_length,
        forecast_horizon=forecast_horizon,
    )

    # Load and add features
    processed_df = preprocessor.load_from_influx(
        [{"time": row["time"], "value": row["value"]} for _, row in df.iterrows()]
    )
    processed_df = preprocessor.prepare_features(processed_df)

    # Ensure target column is first
    feature_cols = ["request_rate"] + [c for c in processed_df.columns if c != "request_rate"]
    processed_df = processed_df[feature_cols]

    logger.info("Features: %s", list(processed_df.columns))
    logger.info("Data shape after preprocessing: %s", processed_df.shape)

    # Train
    model = LSTMPredictor(
        input_size=len(feature_cols),
        sequence_length=sequence_length,
        forecast_horizon=forecast_horizon,
        epochs=epochs,
    )
    metrics = model.train(processed_df)

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODELS_DIR / f"{model_name}_{timestamp}.pt"
    model.save(str(model_path))

    latest_path = MODELS_DIR / f"{model_name}_latest.pt"
    model.save(str(latest_path))

    # Save training report
    report = {
        "model": model_name,
        "timestamp": timestamp,
        "data_points": len(df),
        "features": len(feature_cols),
        "feature_names": list(processed_df.columns),
        "sequence_length": sequence_length,
        "forecast_horizon": forecast_horizon,
        "epochs": epochs,
        "metrics": metrics,
        "model_path": str(model_path),
    }
    report_path = MODELS_DIR / f"{model_name}_{timestamp}_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Training report saved to %s", report_path)
    return report


def main():
    parser = argparse.ArgumentParser(description="Train ML Predictor Models")
    parser.add_argument("--source", type=str, choices=["synthetic", "influxdb"], default="synthetic",
                        help="Data source for training: 'synthetic' or 'influxdb'")
    parser.add_argument("--days", type=int, default=14, help="Days of historical data to use")
    args = parser.parse_args()

    preprocessor = DataPreprocessor()
    df = None

    if args.source == "influxdb":
        logger.info("Attempting to pull real metrics from InfluxDB...")
        if InfluxWriter is None:
            logger.error("Could not import InfluxWriter. Falling back to synthetic.")
        else:
            try:
                # Use environment variables if available, else defaults matching Minikube
                influx_url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
                influx_token = os.environ.get("INFLUXDB_TOKEN", "autoscaler-admin-token")
                influx_org = os.environ.get("INFLUXDB_ORG", "autoscaler-org")
                influx_bucket = os.environ.get("INFLUXDB_BUCKET", "metrics")
                
                writer = InfluxWriter(influx_url, influx_token, influx_org, influx_bucket)
                start_range = f"-{args.days}d"
                raw_data = writer.query_metrics(measurement="app_metrics", field="request_rate", start=start_range)
                
                if not raw_data:
                    logger.warning("Query returned no data. Ensure metrics-collector has run. Falling back to synthetic.")
                else:
                    logger.info("Successfully pulled %d records from InfluxDB.", len(raw_data))
                    df = pd.DataFrame(raw_data)
                    # Convert 'time' to string (from timezone aware datetime) so it works with Prophet below
                    df["time"] = df["time"].dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.error("Failed to fetch from InfluxDB: %s", e)

    if df is None:
        logger.info("Generating synthetic training data...")
        df = preprocessor.generate_synthetic_data(days=args.days)
        logger.info("Generated %d synthetic data points", len(df))

    # Train Prophet
    prophet_report = train_prophet(df)

    # Train LSTM
    lstm_report = train_lstm(df, epochs=30)

    # Summary
    logger.info("\n" + "═" * 60)
    logger.info("TRAINING SUMMARY")
    logger.info("═" * 60)
    logger.info("Prophet — MAE: %.3f, RMSE: %.3f, MAPE: %.2f%%",
                prophet_report["metrics"]["mae"],
                prophet_report["metrics"]["rmse"],
                prophet_report["metrics"]["mape"])
    logger.info("LSTM    — val_loss: %.6f", lstm_report["metrics"]["val_loss"])


if __name__ == "__main__":
    main()
