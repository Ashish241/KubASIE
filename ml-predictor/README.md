# ML Predictor

The ML Predictor component is responsible for forecasting future traffic patterns to enable proactive scaling.

## Features
- Implements Facebook Prophet for capturing daily and weekly seasonalities.
- Uses PyTorch LSTM models for complex, non-linear traffic patterns.
- Exposes predictions to the Scaling Engine.

## Running Locally

```bash
pip install -r requirements.txt

# Train model with synthetic data
python train.py

# Evaluate model
python evaluate.py
```

## Running Tests

```bash
python -m pytest tests/ -v
```
