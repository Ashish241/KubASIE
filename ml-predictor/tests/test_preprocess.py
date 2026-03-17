"""
Tests for ML Predictor preprocessing.
"""

import pytest
import numpy as np
import pandas as pd

from preprocess import DataPreprocessor


@pytest.fixture
def preprocessor():
    return DataPreprocessor(sequence_length=10, forecast_horizon=5)


@pytest.fixture
def sample_df():
    """Create sample time-series DataFrame."""
    dates = pd.date_range(start="2025-01-01", periods=200, freq="min")
    values = np.sin(np.linspace(0, 4 * np.pi, 200)) * 50 + 100
    return pd.DataFrame({"time": dates, "value": values})


class TestDataPreprocessor:

    def test_generate_synthetic_data(self, preprocessor):
        df = preprocessor.generate_synthetic_data(days=2, interval_minutes=5)
        assert len(df) > 0
        assert "time" in df.columns
        assert "value" in df.columns
        assert (df["value"] >= 0).all()

    def test_load_from_influx(self, preprocessor, sample_df):
        influx_data = [{"time": row["time"], "value": row["value"]} for _, row in sample_df.iterrows()]
        df = preprocessor.load_from_influx(influx_data)
        assert len(df) == len(sample_df)
        assert "request_rate" in df.columns

    def test_add_time_features(self, preprocessor, sample_df):
        influx_data = [{"time": row["time"], "value": row["value"]} for _, row in sample_df.iterrows()]
        df = preprocessor.load_from_influx(influx_data)
        df = preprocessor.add_time_features(df)
        assert "hour_sin" in df.columns
        assert "hour_cos" in df.columns
        assert "dow_sin" in df.columns
        assert "is_weekend" in df.columns

    def test_add_lag_features(self, preprocessor, sample_df):
        influx_data = [{"time": row["time"], "value": row["value"]} for _, row in sample_df.iterrows()]
        df = preprocessor.load_from_influx(influx_data)
        df = preprocessor.add_lag_features(df)
        assert "rolling_mean_15m" in df.columns
        assert "lag_1" in df.columns
        assert "rate_of_change" in df.columns

    def test_create_sequences(self, preprocessor):
        data = np.random.randn(100, 3)
        X, y = preprocessor.create_sequences(data)
        expected_seqs = 100 - 10 - 5 + 1
        assert X.shape == (expected_seqs, 10, 3)
        assert y.shape == (expected_seqs, 5)

    def test_split_data_preserves_order(self, preprocessor, sample_df):
        influx_data = [{"time": row["time"], "value": row["value"]} for _, row in sample_df.iterrows()]
        df = preprocessor.load_from_influx(influx_data)
        train, test = preprocessor.split_data(df, train_ratio=0.8)
        # Train should be before test in time
        assert train.index.max() < test.index.min()

    def test_scaler_roundtrip(self, preprocessor):
        data = np.random.randn(50, 2)
        scaled = preprocessor.fit_transform(data)
        assert scaled.min() >= -0.01
        assert scaled.max() <= 1.01
        original = preprocessor.inverse_transform(scaled)
        np.testing.assert_array_almost_equal(data, original, decimal=5)
