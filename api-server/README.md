# API Server

The FastAPI REST API provides the interface for monitoring and configuring the Kubernetes Auto-Scaling Intelligence Engine.

## Features
- Provides REST endpoints for current and historical metrics.
- Exposes traffic predictions and HPA scaling status.
- Allows configuration of scaling thresholds and SLA policies.
- Automatically generates Swagger documentation.

## Running Locally

Make sure you have Python 3.11 installed.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
python -m pytest tests/ -v
```
