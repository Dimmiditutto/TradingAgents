#!/bin/bash
# Script di setup per TradingAgents

echo "🔧 Setup TradingAgents con Chainlit"
echo "======================================"

cd /workspaces/TradingAgents

# Ricrea il virtual environment
echo "📦 Ricreazione virtual environment..."
rm -rf .venv
/usr/bin/python3 -m venv .venv
echo "✅ venv creato"

# Attiva e installa
echo "📦 Installazione dipendenze..."
.venv/bin/python -m pip install --upgrade pip setuptools wheel --quiet
echo "✅ pip aggiornato"

# Installa le dipendenze principali
echo "📦 Installazione chainlit..."
.venv/bin/pip install chainlit --quiet
echo "✅ chainlit installato"

echo "📦 Installazione altre dipendenze..."
.venv/bin/pip install langgraph langchain-openai langchain-anthropic langchain-google-genai pandas yfinance rich questionary python-dotenv --quiet
echo "✅ dipendenze installate"

echo ""
echo "🎉 Setup completato!"
echo ""
echo "Per avviare l'app, esegui:"
echo "  cd /workspaces/TradingAgents/TradingAgents"
echo "  /workspaces/TradingAgents/.venv/bin/python -m chainlit run app.py"
echo ""
echo "O più semplicemente:"
echo "  source /workspaces/TradingAgents/.venv/bin/activate"
echo "  cd TradingAgents"
echo "  chainlit run app.py"
