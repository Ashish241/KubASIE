FROM python:3.11-slim

LABEL project="k8s-autoscaling-intelligence-engine"
LABEL component="ml-predictor"

WORKDIR /app

# Install system dependencies for Prophet
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install CPU-only PyTorch (much smaller than CUDA version)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN python -m cmdstanpy.install_cmdstan --cores 2

COPY *.py .
COPY models/ models/

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default: run the Prediction FastAPI Service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
