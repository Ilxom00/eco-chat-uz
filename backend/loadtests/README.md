# eco-chat.uz — Production Load & Stress Testing

This directory contains scripts and configurations for load and stress testing the `eco-chat.uz` application using Locust.

## Directory Structure
- `locustfile.py`: Main Locust load test suite implementing realistic employee and admin flows.
- `results/`: Directory for keeping test runs and reports.

## Prerequisites
1. Install requirements:
   ```bash
   pip install locust
   ```

## Running the load tests
Run the load tests locally targeting the production server URL:
```bash
locust -f locustfile.py --host https://eco-chat.uz
```
Open [http://localhost:8089](http://localhost:8089) to configure the target phases (10 to 200 concurrent users) and visualize RPS, latency percentiles, and failure rates.
