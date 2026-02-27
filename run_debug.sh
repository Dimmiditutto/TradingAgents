#!/bin/bash
# Simple startup script with full logging

echo "🛑 Killing old processes..."
pkill -9 -f "chainlit run" 2>/dev/null || true
sleep 1

echo "🚀 Starting Chainlit with full logging..."
echo "============================================"
date

cd /workspaces/TradingAgents/web
source /workspaces/TradingAgents/.venv/bin/activate

# Export debug
export PYTHONUNBUFFERED=1
export LOGLEVEL=DEBUG

# Start with output
python -m chainlit run app.py --host 0.0.0.0 --port 8000

echo "============================================"
echo "Server stopped"
