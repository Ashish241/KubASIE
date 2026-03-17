FROM python:3.11-slim

LABEL project="k8s-autoscaling-intelligence-engine"
LABEL component="metrics-collector"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "collector.py"]
