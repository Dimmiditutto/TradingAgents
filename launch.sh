#!/bin/bash
# Script per lanciare TradingAgents Web App

echo "🚀 TradingAgents Web App Launcher"
echo "=================================="
echo ""

# Verifica dipendenze
echo "✓ Checking environment..."

# Attiva venv se esiste
if [ -d "venv" ]; then
    echo "✓ Virtual environment found, activating..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found"
    echo "Creating one now..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Installa dipendenze
echo "✓ Installing dependencies..."
pip install -q -r requirements.txt
pip install -q reportlab openpyxl plotly kaleido

# Verifica variabili d'ambiente
echo "✓ Checking environment variables..."

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set!"
    echo "   Set it with: export OPENAI_API_KEY=sk_your_key"
fi

# Crea cartelle se non esistono
mkdir -p reports dashboards

# Lancia app
echo ""
echo "🎉 Launching TradingAgents Web App..."
echo "📍 Access it at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

chainlit run app.py
