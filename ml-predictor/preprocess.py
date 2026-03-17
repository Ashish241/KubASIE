"""
Data Preprocessing — Feature engineering for traffic forecasting.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger("ml-predictor.preprocess")


class DataPreprocessor:
    """Prepares raw time-series data for ML model training."""

    def __init__(self, sequence_length: int = 60, forecast_horizon: int = 15):
        """
        Args:
            sequence_length: Number of past time steps to use as input features.
            forecast_horizon: Number of future time steps to predict.
        """
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def load_from_influx(self, influx_data: list) -> pd.DataFrame:
        """Convert InfluxDB query results to a DataFrame."""
        df = pd.DataFrame(influx_data)
        if df.empty:
            logger.warning("No data received from InfluxDB")
            return df

        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time").sort_index()
        df = df.rename(columns={"value": "request_rate"})
        return df

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal features for capturing seasonality."""
        df = df.copy()
        df["hour"] = df.index.hour
        df["day_of_week"] = df.index.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Cyclical encoding of hour (so 23:00 is close to 00:00)
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

        # Cyclical encoding of day of week
        df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

        return df

    def add_lag_features(self, df: pd.DataFrame, column: str = "request_rate") -> pd.DataFrame:
        """Add rolling statistics and lag features."""
        df = df.copy()

        # Rolling window features
        df["rolling_mean_15m"] = df[column].rolling(window=15, min_periods=1).mean()
        df["rolling_std_15m"] = df[column].rolling(window=15, min_periods=1).std().fillna(0)
        df["rolling_mean_60m"] = df[column].rolling(window=60, min_periods=1).mean()
        df["rolling_max_60m"] = df[column].rolling(window=60, min_periods=1).max()

        # Lag features
        for lag in [1, 5, 15, 30, 60]:
            df[f"lag_{lag}"] = df[column].shift(lag)

        # Rate of change
        df["rate_of_change"] = df[column].pct_change(periods=5).fillna(0)
        df["rate_of_change"] = df["rate_of_change"].clip(-10, 10)  # clip extreme values

        # Drop rows with NaN from lag/rolling (at the beginning)
        df = df.dropna()
        return df

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Full feature engineering pipeline."""
        df = self.add_time_features(df)
        df = self.add_lag_features(df)
        return df

    def create_sequences(
        self, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create input/output sequences for LSTM.

        Args:
            data: 2D array of shape (n_samples, n_features).
                  The first column is the target variable.

        Returns:
            X: shape (n_sequences, sequence_length, n_features)
            y: shape (n_sequences, forecast_horizon)
        """
        X, y = [], []
        for i in range(len(data) - self.sequence_length - self.forecast_horizon + 1):
            X.append(data[i : i + self.sequence_length])
            # Target is only the first column (request_rate)
            y.append(data[i + self.sequence_length : i + self.sequence_length + self.forecast_horizon, 0])

        return np.array(X), np.array(y)

    def split_data(
        self, df: pd.DataFrame, train_ratio: float = 0.8
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Time-series aware train/test split (no shuffling — preserves temporal order).
        """
        split_idx = int(len(df) * train_ratio)
        train = df.iloc[:split_idx]
        test = df.iloc[split_idx:]
        logger.info("Split data: train=%d, test=%d", len(train), len(test))
        return train, test

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """Fit the scaler on data and return normalized values."""
        return self.scaler.fit_transform(data)

    def transform(self, data: np.ndarray) -> np.ndarray:
        """Transform data using the already-fitted scaler."""
        return self.scaler.transform(data)

    def inverse_transform(self, data: np.ndarray) -> np.ndarray:
        """Reverse the scaling to get original values."""
        return self.scaler.inverse_transform(data)

    def generate_synthetic_data(
        self, days: int = 14, interval_minutes: int = 1
    ) -> pd.DataFrame:
        """
        Generate synthetic traffic data for development/testing.
        Simulates realistic diurnal patterns with noise.
        """
        logger.info("Generating %d days of synthetic traffic data", days)
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(days=days),
            end=datetime.now(),
            freq=f"{interval_minutes}min",
        )

        n = len(timestamps)
        hours = np.array([t.hour + t.minute / 60 for t in timestamps])

        # Base diurnal pattern (peak at 10am and 3pm, low at 3am)
        base = 50 + 30 * np.sin(2 * np.pi * (hours - 6) / 24)
        base += 15 * np.sin(2 * np.pi * (hours - 12) / 12)

        # Weekly pattern (lower on weekends)
        day_of_week = np.array([t.dayofweek for t in timestamps])
        weekend_factor = np.where(day_of_week >= 5, 0.6, 1.0)
        base *= weekend_factor

        # Add realistic noise + occasional spikes
        noise = np.random.normal(0, 5, n)
        spikes = np.random.choice([0, 1], size=n, p=[0.995, 0.005])
        spike_magnitude = spikes * np.random.uniform(50, 150, n)

        request_rate = np.maximum(0, base + noise + spike_magnitude)

        df = pd.DataFrame({
            "time": timestamps,
            "value": request_rate,
        })
        return df
