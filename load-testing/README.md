# Load Testing

The Load Testing directory contains Locust scripts to simulate traffic against the Target Application.

## Features
- Simulates sudden traffic spikes and continuous load to evaluate scaling behavior.
- Provides a web UI via Locust for monitoring test execution.

## Running Locally

```bash
pip install -r requirements.txt

# Run headless load test
locust -f locustfile.py --headless -u 50 -r 5 --run-time 10m --host http://localhost:5000

# Or run with the web UI
locust -f locustfile.py --host http://localhost:5000
# Then open http://localhost:8089 in your browser
```
