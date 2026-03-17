"""
Model Evaluation — Backtesting and model comparison framework.
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

from preprocess import DataPreprocessor
from model import ProphetPredictor

logger = logging.getLogger("ml-predictor.evaluate")


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def backtesting_walk_forward(
    df: pd.DataFrame,
    model_class,
    initial_train_size: int = 5000,
    test_window: int = 60,
    step: int = 60,
    horizon: int = 15,
) -> Dict:
    """
    Walk-forward backtesting for time-series models.

    Trains on an expanding window and evaluates on rolling test windows.
    This is the gold standard for time-series model evaluation.

    Args:
        df: Full dataset with 'time' and 'value' columns.
        model_class: Class to instantiate (e.g., ProphetPredictor).
        initial_train_size: Minimum training data points.
        test_window: Number of points in each test window.
        step: How many points to advance between iterations.
        horizon: Prediction horizon in minutes.

    Returns:
        Aggregate evaluation metrics and per-window breakdown.
    """
    logger.info("Running walk-forward backtest (initial_train=%d, step=%d, horizon=%d)",
                initial_train_size, step, horizon)

    all_mae, all_rmse, all_mape = [], [], []
    windows: List[Dict] = []

    # Prepare data
    prophet_df = df.rename(columns={"time": "ds", "value": "y"})[["ds", "y"]].copy()
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

    n = len(prophet_df)
    idx = initial_train_size

    while idx + test_window <= n:
        train_data = prophet_df.iloc[:idx]
        test_data = prophet_df.iloc[idx : idx + min(horizon, test_window)]

        try:
            model = model_class()
            model.train(train_data)
            predictions = model.predict(horizon=len(test_data))

            y_true = test_data["y"].values
            y_pred = predictions["yhat"].values[: len(y_true)]

            mae = mean_absolute_error(y_true, y_pred)
            rmse = root_mean_squared_error(y_true, y_pred)
            mape = mean_absolute_percentage_error(y_true, y_pred)

            all_mae.append(mae)
            all_rmse.append(rmse)
            all_mape.append(mape)

            windows.append({
                "train_size": len(train_data),
                "test_start": str(test_data.iloc[0]["ds"]),
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "mape": round(mape, 2),
            })

        except Exception as e:
            logger.warning("Backtest window failed at idx=%d: %s", idx, e)

        idx += step

    results = {
        "total_windows": len(windows),
        "avg_mae": round(float(np.mean(all_mae)), 4) if all_mae else None,
        "avg_rmse": round(float(np.mean(all_rmse)), 4) if all_rmse else None,
        "avg_mape": round(float(np.mean(all_mape)), 2) if all_mape else None,
        "std_mae": round(float(np.std(all_mae)), 4) if all_mae else None,
        "windows": windows,
    }

    logger.info("Backtest complete — %d windows, avg MAE: %s, avg RMSE: %s, avg MAPE: %s%%",
                results["total_windows"], results["avg_mae"], results["avg_rmse"], results["avg_mape"])

    return results


def compare_models(df: pd.DataFrame) -> Dict:
    """Compare Prophet and LSTM models on the same dataset."""
    logger.info("═" * 60)
    logger.info("MODEL COMPARISON")
    logger.info("═" * 60)

    results = {}

    # Prophet backtest
    logger.info("\n--- Prophet ---")
    results["prophet"] = backtesting_walk_forward(
        df, ProphetPredictor,
        initial_train_size=3000,
        step=500,
    )

    return results


def main():
    """Run evaluation on synthetic data."""
    preprocessor = DataPreprocessor()
    df = preprocessor.generate_synthetic_data(days=14)
    logger.info("Generated %d synthetic data points for evaluation", len(df))

    results = compare_models(df)

    print("\n" + "═" * 60)
    print("EVALUATION RESULTS")
    print("═" * 60)
    for model_name, metrics in results.items():
        print(f"\n{model_name.upper()}:")
        print(f"  Windows: {metrics['total_windows']}")
        print(f"  MAE:     {metrics['avg_mae']} ± {metrics['std_mae']}")
        print(f"  RMSE:    {metrics['avg_rmse']}")
        print(f"  MAPE:    {metrics['avg_mape']}%")


if __name__ == "__main__":
    main()
