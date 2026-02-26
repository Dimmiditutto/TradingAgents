#!/bin/bash
# Script per avviare Chainlit in modo stabile con GitHub Codespaces

cd /workspaces/TradingAgents/web

# Attiva l'ambiente virtuale
source /workspaces/TradingAgents/.venv/bin/activate

# Export le variabili d'ambiente necessarie
export CHAINLIT_HOST="0.0.0.0"
export CHAINLIT_PORT="8000"

# Kill existing chainlit processes
echo "🔍 Checking for existing Chainlit processes..."
pkill -9 -f "chainlit run app.py" 2>/dev/null && echo "✅ Killed existing processes" || echo "✓ No processes to kill"
sleep 2

echo "🚀 Starting Chainlit on http://0.0.0.0:8000"
echo "📝 Keep this terminal open!"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start Chainlit with all necessary flags
chainlit run app.py \
  --host 0.0.0.0 \
  --port 8000 \
  --headless
