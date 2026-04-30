#!/bin/bash

# Get the script directory and navigate to the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Ensure subdirectories exist
mkdir -p tmp data log

echo "Starting Translation API service..."

# Run the FastAPI server using uv
# Using --app-dir src to find the translator package
uv run uvicorn translator.main:app \
    --app-dir src \
    --host ${API_HOST:-0.0.0.0} \
    --port ${API_PORT:-8000} \
    --log-level info \
    2>&1 | tee -a log/server.log
