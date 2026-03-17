# Target Application

The Target Application is a sample Python Flask application used for demonstrating the autoscaling capabilities of the engine.

## Features
- A simple Flask API that exposes Prometheus metrics.
- Simulates CPU and memory load for testing the HPA.
- Serves as the workload that the scaling engine aims to optimize.

## Running Locally

```bash
pip install -r requirements.txt
python app.py
```
