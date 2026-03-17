# Scaling Engine

The Scaling Engine is the core component responsible for actively adjusting the Kubernetes Horizontal Pod Autoscaler (HPA) rules.

## Features
- Operates a hybrid policy evaluating both reactive metrics (CPU/Memory/RPS) and ML traffic predictions.
- Enforces anti-flapping mechanisms (cooldowns) to prevent rapid oscillating scaling events.
- Interacts directly with the Kubernetes API to patch HPA objects.

## Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```
