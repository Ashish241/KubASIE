# Metrics Collector

The Metrics Collector scrapes data from Prometheus and writes it into InfluxDB for historical storage and ML training.

## Features
- Connects to Prometheus to extract real-time application metrics (RPS, Latency, CPU, Memory).
- Writes high-resolution metrics to InfluxDB 2.x.
- Exposes a health endpoint to monitor the collector pipeline.

## Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```
