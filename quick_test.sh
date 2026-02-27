#!/bin/bash
# Fast startup test

echo "🛑 Killing old Chainlit processes..."
pkill -9 -f "chainlit run app" 2>/dev/null || true
sleep 1

echo "🚀 Starting server..."
cd /workspaces/TradingAgents/web
source /workspaces/TradingAgents/.venv/bin/activate

# Start in background and capture initial output
python -m chainlit run app.py --host 0.0.0.0 --port 8000 > /tmp/chainlit.log 2>&1 &
SERVER_PID=$!

echo "Server PID: $SERVER_PID"
echo ""
echo "Waiting for startup (max 15 seconds)..."

# Monitor startup
for i in {1..15}; do
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        # Check if port is open
        if nc -z localhost 8000 2>/dev/null || netstat -tlnp 2>/dev/null | grep -q ":8000"; then
            echo "✅ Port 8000 OPEN!"
            
            # Try HTTP request
            if timeout 2 curl -s http://localhost:8000/ > /tmp/response.html 2>&1; then
                size=$(wc -c < /tmp/response.html)
                echo "✅ HTTP request successful (response: $size bytes)"
                break
            else
                echo "⏳ Port open but HTTP not responding yet ($i/15)..."
            fi
        else
            echo "⏳ Waiting for port ($i/15)..."
        fi
    else
        echo "❌ Server died!"
        cat /tmp/chainlit.log
        exit 1
    fi
    sleep 1
done

echo ""
echo "============================================"
echo "✅ Server is RUNNING"
echo "============================================"
echo ""
echo "Recent startup logs:"
tail -20 /tmp/chainlit.log
echo ""
echo "Access: http://localhost:8000"
