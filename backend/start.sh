#!/bin/bash

# 1. Start Celery with ONLY 1 worker to save memory
celery -A worker worker --loglevel=info --concurrency=1 &

# 2. Start the FastAPI web server
uvicorn main:app --host 0.0.0.0 --port $PORT