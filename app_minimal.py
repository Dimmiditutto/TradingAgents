"""
TradingAgents - Versione Minimalista
Carica moduli pesanti SOLO quando necessario
"""

import sys
import os
from pathlib import Path

# Setup path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import chainlit as cl
from datetime import datetime
from dotenv import load_dotenv

# Carica .env
load_dotenv()

# ============================================================================
# GLOBAL STATE - NO HEAVY IMPORTS HERE
# ============================================================================
ta = None
user_config = None
config = {
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance", 
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
}

# ============================================================================
# LAZY LOADERS - Import only when called
# ============================================================================

def get_ta():
    """Lazy load TradingAgentsGraph"""
    global ta
    if ta is None:
        try:
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            ta = TradingAgentsGraph(debug=False, config=config)
        except Exception as e:
            cl.Message(f"❌ Error loading TradingAgentsGraph: {e}").send()
            ta = None
    return ta

def get_report_gen():
    """Lazy load ReportGenerator"""
    try:
        from tradingagents.utils.report_generator import ReportGenerator
        return ReportGenerator(output_dir="./reports")
    except Exception as e:
        cl.Message(f"❌ Error loading ReportGenerator: {e}").send()
        return None

def get_dashboard_gen():
    """Lazy load DashboardGenerator"""
    try:
        from tradingagents.utils.dashboard import DashboardGenerator
        return DashboardGenerator(output_dir="./dashboards")
    except Exception as e:
        cl.Message(f"❌ Error loading DashboardGenerator: {e}").send()
        return None

# ============================================================================
# CHAINLIT EVENTS
# ============================================================================

@cl.on_chat_start
async def start():
    """Minimal startup - no heavy loads"""
    welcome = """
🚀 **TradingAgents** - Sistema di Trading Automatico

💡 **Come usare:**
- `CONFIGURA` - Setup completo
- `ANALIZZA AAPL` - Analizza rapida
- `AIUTO` - Mostra comandi

⚡ **Avvio minimale**: i moduli pesanti vengono caricati al primo comando.
"""
    await cl.Message(content=welcome).send()


@cl.on_message
async def main(message: cl.Message):
    """Gestione messaggi"""
    text = message.content.strip().upper()
    
    if text.startswith("ANALIZZA"):
        await analyze_stock(text)
    elif text == "CONFIGURA":
        await configure()
    elif text == "AIUTO":
        await help_command()
    else:
        await cl.Message(content="❓ Comando non riconosciuto. Digita `AIUTO` per i dettagli.").send()


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def analyze_stock(user_input: str):
    """Esegui analisi trading"""
    global ta
    
    parts = user_input.split()
    if len(parts) < 2:
        await cl.Message(content="❌ Uso: `ANALIZZA TICKER [DATA]`").send()
        return
    
    ticker = parts[1].upper()
    date = parts[2] if len(parts) > 2 else datetime.now().strftime("%Y-%m-%d")
    
    await cl.Message(content=f"⏳ Caricamento TradingAgentsGraph per {ticker}...").send()
    
    ta = get_ta()
    if ta is None:
        await cl.Message(content="❌ Impossibile caricare TradingAgentsGraph").send()
        return
    
    try:
        await cl.Message(content=f"🔄 Analizzando {ticker} per {date}...").send()
        _, decision = ta.propagate(ticker, date)
        
        await cl.Message(content=f"✅ **Decisione**: {decision[:100]}...").send()
    except Exception as e:
        await cl.Message(content=f"❌ Errore durante l'analisi: {str(e)[:200]}").send()


async def configure():
    """Setup interattivo"""
    await cl.Message(content="⚙️ Configurazione non ancora implementata in versione minimale.").send()


async def help_command():
    """Mostra aiuto"""
    help_text = """
📚 **Comandi disponibili:**

1. **ANALIZZA TICKER [DATA]**
   Esegui analisi trading su un titolo
   Esempi:
   - `ANALIZZA AAPL`
   - `ANALIZZA NVDA 2024-05-10`

2. **CONFIGURA**
   Setup completo con opzioni custom

3. **AIUTO**
   Mostra questo messaggio

⚡ **Nota**: Il primo comando caricherà i moduli pesanti (10-20 secondi)
"""
    await cl.Message(content=help_text).send()
