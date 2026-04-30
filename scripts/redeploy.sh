#!/bin/bash
set -e

# Redeployment Script for Translator
# Usage: ./scripts/redeploy.sh

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==========================================="
echo "   REDEPLOYING TRANSLATOR   "
echo "==========================================="

# Check for port conflicts
PORT_API=28002
CHECK_PORTS=($PORT_API)

for PORT in "${CHECK_PORTS[@]}"; do
    if ss -tulpn 2>/dev/null | grep -q ":$PORT "; then
        echo "WARNING: Port $PORT is already in use."
        PID=$(lsof -t -i :$PORT 2>/dev/null || ss -tulpn 2>/dev/null | grep ":$PORT " | awk -F'pid=' '{print $2}' | cut -d, -f1)
        if [ ! -z "$PID" ]; then
            echo "Found process $PID on $PORT. Attempting to kill it..."
            kill -9 $PID 2>/dev/null || true
        fi
    fi

    # More aggressive check for rootlessport dangling processes
    DANGLING_PIDS=$(ps -ef | grep "rootlessport.*:$PORT" | grep -v grep | awk '{print $2}')
    if [ ! -z "$DANGLING_PIDS" ]; then
        echo "Found dangling rootlessport processes for port $PORT: $DANGLING_PIDS. Killing them..."
        kill -9 $DANGLING_PIDS 2>/dev/null || true
    fi
done

echo "Step 1: Stopping existing containers (podman-compose down)..."
podman-compose down || true

echo "Step 2: Building and starting containers (podman-compose up -d --build)..."
podman-compose up -d --build --remove-orphans

echo "Step 3: Verification..."
podman-compose ps

echo "==========================================="
echo "   Redeployment attempted! Checking status...   "
echo "==========================================="

if podman-compose ps | grep -q "Up"; then
    echo "SUCCESS: Containers are running."
else
    echo "FAILURE: No containers seem to be running. Check logs with 'podman-compose logs'."
fi
