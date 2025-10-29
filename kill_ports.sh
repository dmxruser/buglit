#!/bin/bash
# This script finds and kills any processes running on ports 3000 and 8000.

echo "Attempting to clear ports 3000 and 8000..."

# The '2>/dev/null' part suppresses errors if no processes are found
kill $(lsof -ti :3000 -ti :8000) 2>/dev/null

echo "Ports have been cleared."
