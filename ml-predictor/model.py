"""
Model Definitions — Prophet and LSTM models for traffic prediction.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("ml-predictor.model")


class BasePredictor(ABC):
    """Abstract base class for all prediction models."""

    @abstractmethod
    def train(self, df: pd.DataFrame) -> Dict:
        """Train the model on historical data. Returns training metrics."""
        pass

    @abstractmethod
    def predict(self, horizon: int) -> np.ndarray:
        """Generate predictions for the next `horizon` time steps."""
        pass

    @abstractmethod
    def save(self, path: str):
        """Save model to disk."""
        pass

    @abstractmethod
    def load(self, path: str):
        """Load model from disk."""
        pass


class ProphetPredictor(BasePredictor):
    """Facebook Prophet model for traffic forecasting."""

    def __init__(self, interval_width: float = 0.95):
        self.interval_width = interval_width
        self.model = None

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train Prophet on historical data.

        Args:
            df: DataFrame with 'ds' (datetime) and 'y' (value) columns,
                following Prophet's expected format.
        """
        from prophet import Prophet

        logger.info("Training Prophet model on %d data points", len(df))

        self.model = Prophet(
            interval_width=self.interval_width,
            daily_seasonality=True,
            weekly_seasonality=True,
            changepoint_prior_scale=0.05,
        )
        self.model.fit(df)

        # In-sample predictions for training metrics
        train_pred = self.model.predict(df[["ds"]])
        y_true = df["y"].values
        y_pred = train_pred["yhat"].values

        metrics = self._compute_metrics(y_true, y_pred)
        logger.info("Prophet training — MAE: %.3f, RMSE: %.3f, MAPE: %.2f%%",
                     metrics["mae"], metrics["rmse"], metrics["mape"])
        return metrics

    def predict(self, horizon: int = 15) -> pd.DataFrame:
        """
        Predict the next `horizon` minutes.

        Returns DataFrame with: ds, yhat, yhat_lower, yhat_upper
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        future = self.model.make_future_dataframe(periods=horizon, freq="min")
        forecast = self.model.predict(future)

        # Return only the future predictions
        result = forecast.tail(horizon)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        result["yhat"] = result["yhat"].clip(lower=0)  # Can't have negative traffic
        return result

    def save(self, path: str):
        import pickle
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info("Prophet model saved to %s", path)

    def load(self, path: str):
        import pickle
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        logger.info("Prophet model loaded from %s", path)

    @staticmethod
    def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        mae = np.mean(np.abs(y_true - y_pred))
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        # Avoid division by zero for MAPE
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else 0.0
        return {"mae": float(mae), "rmse": float(rmse), "mape": float(mape)}


class LSTMPredictor(BasePredictor):
    """PyTorch LSTM model for multi-step traffic forecasting."""

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        epochs: int = 50,
        batch_size: int = 32,
        sequence_length: int = 60,
        forecast_horizon: int = 15,
    ):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.model = None
        self._scaler = None

    def _build_model(self):
        """Build the PyTorch LSTM network."""
        import torch
        import torch.nn as nn

        class LSTMNetwork(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout, forecast_horizon):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    dropout=dropout if num_layers > 1 else 0,
                    batch_first=True,
                )
                self.fc = nn.Sequential(
                    nn.Linear(hidden_size, hidden_size // 2),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_size // 2, forecast_horizon),
                )

            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                # Use the last time step's output
                out = self.fc(lstm_out[:, -1, :])
                return out

        return LSTMNetwork(
            self.input_size,
            self.hidden_size,
            self.num_layers,
            self.dropout,
            self.forecast_horizon,
        )

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train the LSTM model.

        Args:
            df: DataFrame with features. First column should be the target.
        """
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        from sklearn.preprocessing import MinMaxScaler

        logger.info("Training LSTM model on %d samples", len(df))

        # Scale data
        values = df.values.astype(np.float32)
        self._scaler = MinMaxScaler()
        scaled = self._scaler.fit_transform(values)
        self.input_size = scaled.shape[1]

        # Create sequences
        X, y = self._create_sequences(scaled)
        logger.info("Created %d sequences (seq_len=%d, features=%d, horizon=%d)",
                     len(X), self.sequence_length, self.input_size, self.forecast_horizon)

        # Split - last 20% for validation
        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        # PyTorch DataLoaders
        train_ds = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
        val_ds = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=False)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)

        # Build & train
        self.model = self._build_model()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

        best_val_loss = float("inf")
        history = {"train_loss": [], "val_loss": []}

        for epoch in range(self.epochs):
            # Training
            self.model.train()
            train_losses = []
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                pred = self.model(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(loss.item())

            # Validation
            self.model.eval()
            val_losses = []
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    pred = self.model(X_batch)
                    loss = criterion(pred, y_batch)
                    val_losses.append(loss.item())

            avg_train = np.mean(train_losses)
            avg_val = np.mean(val_losses)
            history["train_loss"].append(avg_train)
            history["val_loss"].append(avg_val)
            scheduler.step(avg_val)

            if avg_val < best_val_loss:
                best_val_loss = avg_val

            if (epoch + 1) % 10 == 0:
                logger.info("Epoch %d/%d — train_loss: %.6f, val_loss: %.6f",
                             epoch + 1, self.epochs, avg_train, avg_val)

        metrics = {
            "train_loss": float(history["train_loss"][-1]),
            "val_loss": float(history["val_loss"][-1]),
            "best_val_loss": float(best_val_loss),
        }
        logger.info("LSTM training complete — best_val_loss: %.6f", best_val_loss)
        return metrics

    def predict(self, horizon: int = 15) -> np.ndarray:
        """Generate predictions using the trained LSTM."""
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")
        # For real usage, this would take the last sequence_length data points
        # and run inference through the LSTM. Simplified here.
        raise NotImplementedError("Use predict_from_sequence() with actual input data.")

    def predict_from_sequence(self, sequence: np.ndarray) -> np.ndarray:
        """
        Predict from a specific input sequence.

        Args:
            sequence: shape (sequence_length, n_features) — raw (unscaled) values

        Returns:
            predictions: shape (forecast_horizon,) — unscaled predicted values
        """
        import torch

        if self.model is None or self._scaler is None:
            raise RuntimeError("Model not trained or scaler not fitted.")

        self.model.eval()
        scaled = self._scaler.transform(sequence)
        x = torch.FloatTensor(scaled).unsqueeze(0)  # (1, seq_len, features)

        with torch.no_grad():
            pred_scaled = self.model(x).numpy()[0]  # (forecast_horizon,)

        # Inverse transform — predictions are for the first feature (target)
        # Create dummy array with same shape as scaler expects
        dummy = np.zeros((len(pred_scaled), self._scaler.n_features_in_))
        dummy[:, 0] = pred_scaled
        pred_unscaled = self._scaler.inverse_transform(dummy)[:, 0]

        return np.maximum(0, pred_unscaled)  # Clip negative predictions

    def _create_sequences(self, data: np.ndarray):
        X, y = [], []
        for i in range(len(data) - self.sequence_length - self.forecast_horizon + 1):
            X.append(data[i : i + self.sequence_length])
            y.append(data[i + self.sequence_length : i + self.sequence_length + self.forecast_horizon, 0])
        return np.array(X), np.array(y)

    def save(self, path: str):
        import torch
        import pickle

        torch.save(self.model.state_dict(), path)
        # Save scaler separately
        scaler_path = path.replace(".pt", "_scaler.pkl")
        with open(scaler_path, "wb") as f:
            pickle.dump(self._scaler, f)
        logger.info("LSTM model saved to %s", path)

    def load(self, path: str):
        import torch
        import pickle

        scaler_path = path.replace(".pt", "_scaler.pkl")
        with open(scaler_path, "rb") as f:
            self._scaler = pickle.load(f)

        # Set input_size from the loaded scaler before building the model
        if hasattr(self._scaler, "n_features_in_"):
            self.input_size = self._scaler.n_features_in_
            
        self.model = self._build_model()
        self.model.load_state_dict(torch.load(path, weights_only=True))
        self.model.eval()

        logger.info("LSTM model loaded from %s with input_size=%d", path, self.input_size)
