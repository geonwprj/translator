#!/bin/bash

echo "Stopping Translation API service..."

# Find and kill the uvicorn process running translator.main:app
# We use -f to match the full command line
pkill -f "uvicorn translator.main:app"

if [ $? -eq 0 ]; then
    echo "Service stopped successfully."
else
    echo "Service was not running or could not be stopped."
fi
