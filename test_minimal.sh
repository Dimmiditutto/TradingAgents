#!/bin/bash
# Test Chainlit with minimal app

cd /workspaces/TradingAgents/web
source /workspaces/TradingAgents/.venv/bin/activate

# Kill old processes
pkill -9 -f "chainlit run" 2>/dev/null
sleep 2

# Test minimal app
echo "🚀 Starting minimal app..."
echo "============================================="

timeout 30 python -m chainlit run app_minimal.py --host 0.0.0.0 --port 8000 2>&1 &
CHAINLIT_PID=$!

# Wait and check
sleep 5
if ps -p $CHAINLIT_PID > /dev/null; then
    echo "✅ Server is RUNNING (PID: $CHAINLIT_PID)"
    echo "✅ No exit code 137 crash!"
    echo ""
    echo "Test successful - server stayed alive for 5+ seconds"
    echo ""
    kill $CHAINLIT_PID 2>/dev/null
else
    echo "❌ Server CRASHED or exited (PID: $CHAINLIT_PID)"
    ps -p $CHAINLIT_PID > /dev/null || echo "   Exit code indicates process died"
fi
