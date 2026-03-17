"""
Tests for training pipeline.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from preprocess import DataPreprocessor


class TestTrainingPipeline:

    def test_synthetic_data_for_training(self):
        """Verify synthetic data is suitable for training."""
        preprocessor = DataPreprocessor()
        df = preprocessor.generate_synthetic_data(days=7, interval_minutes=1)

        assert len(df) > 5000
        assert df["value"].mean() > 0
        assert df["value"].std() > 0

    def test_prophet_data_format(self):
        """Verify data can be converted to Prophet format."""
        preprocessor = DataPreprocessor()
        df = preprocessor.generate_synthetic_data(days=2)

        prophet_df = df.rename(columns={"time": "ds", "value": "y"})
        assert "ds" in prophet_df.columns
        assert "y" in prophet_df.columns
        assert len(prophet_df) > 0
