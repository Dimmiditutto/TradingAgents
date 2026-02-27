#!/bin/bash
# Kill and restart script

echo "🛑 Killing old processes..."
pkill -9 -f "chainlit run" 2>/dev/null || true
sleep 2

# Find and kill any remaining processes on port 8000
PORT_PID=$(lsof -ti :8000 2>/dev/null)
if [ ! -z "$PORT_PID" ]; then
    echo "Found process on port 8000: $PORT_PID"
    kill -9 $PORT_PID 2>/dev/null || true
    sleep 1
fi

echo "✅ Port cleared"
echo ""
echo "🚀 Starting Chainlit..."
echo "============================================"

cd /workspaces/TradingAgents/web
source /workspaces/TradingAgents/.venv/bin/activate
python -m chainlit run app.py --host 0.0.0.0 --port 8000
