#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Start the backend server
echo "Starting FastAPI server on port 8000"
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start the frontend server
echo "Starting Vite server on port 3000"
npx vite --port 3000 &
