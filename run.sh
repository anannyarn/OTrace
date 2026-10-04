#!/bin/bash
# OTrace Startup Script

set -e

echo "=== 1. Checking Python environment ==="
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "=== 2. Installing dependencies ==="
pip install -r requirements.txt

echo "=== 3. Training calibrated ML model ==="
python -m eval.train

echo "=== 4. Running unit test suite ==="
pytest -v

echo "=== 5. Running evaluation benchmarks ==="
python -m eval.evaluate

echo "=== 6. Starting OTrace Web Server ==="
echo "Access OTrace at http://127.0.0.1:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000
