"""
TradingAgents - App Web Interattiva con Chainlit
Interfaccia completa con Dashboard, Report e Grafici
"""

import chainlit as cl
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Import TradingAgents
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.utils.report_generator import ReportGenerator
from tradingagents.utils.dashboard import DashboardGenerator

# Configurazione
config = DEFAULT_CONFIG.copy()
config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}

# Inizializza generatori
report_gen = ReportGenerator(output_dir="./reports")
dashboard_gen = DashboardGenerator(output_dir="./dashboards")

# Istanza globale TradingAgents
ta = None


@cl.on_chat_start
async def start():
    """Inizializzazione dell'app"""
    global ta
    
    # Inizializza TradingAgents
    ta = TradingAgentsGraph(debug=False, config=config)
    
    # Messaggio di benvenuto
    await cl.Message(
        content="""
🚀 **Benvenuto in TradingAgents!**

Sistema automatico di analisi trading con intelligenza artificiale multi-agente.

📚 **Come usarlo:**
Inserisci il comando nel formato:
```
ANALIZZA <TICKER> [DATA]
```

**Esempi:**
- `ANALIZZA NVDA` (ultimo giorno)
- `ANALIZZA AAPL 2024-05-10` (data specifica)
- `LISTA` (vedi asset disponibili)
- `AIUTO` (mostra tutte le opzioni)

⚙️ **Le tue analisi includeranno:**
✅ Decisione trading (acquisto/vendita/attesa)
✅ Analisi del sentiment degli agenti
✅ Dashboard interattivo con grafici
✅ Report scaricabile in PDF
✅ Dati in Excel per analisi ulteriore

Inizia digitando un comando! 🎯
        """.strip()
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Gestisci i messaggi dell'utente"""
    global ta
    
    user_input = message.content.strip().upper()
    
    try:
        # Comando AIUTO
        if user_input == "AIUTO" or user_input == "HELP":
            await show_help()
            return
        
        # Comando LISTA
        if user_input == "LISTA" or user_input == "LIST":
            await show_assets()
            return
        
        # Comando ANALIZZA
        if user_input.startswith("ANALIZZA") or user_input.startswith("ANALYZE"):
            await analyze_stock(user_input)
            return
        
        # Fallback
        await cl.Message(
            content="""❌ Comando non riconosciuto.

Comandi disponibili:
- `ANALIZZA <TICKER>` - Analizza un titolo
- `LISTA` - Mostra asset disponibili
- `AIUTO` - Mostra questa guida
            """.strip()
        ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ **Errore:** {str(e)}\n\nProva di nuovo con `AIUTO` per le opzioni."
        ).send()


async def show_help():
    """Mostra guida completa"""
    help_text = """
📖 **GUIDA COMPLETA**

**COMANDI DISPONIBILI:**

1️⃣ ANALIZZA <TICKER> [DATA]
   Esegue analisi completa di un titolo
   - TICKER: simbolo del titolo (es. NVDA, AAPL)
   - DATA: opzionale, formato YYYY-MM-DD
   
   Esempio: `ANALIZZA NVDA 2024-05-10`

2️⃣ LISTA
   Mostra i principali asset su cui puoi fare analisi

3️⃣ AIUTO
   Mostra questa guida

**COSA RICEVI DA UN'ANALISI:**

📊 Decisione Trading
   - ACQUISTO (💚 Rialzista)
   - VENDITA (❌ Ribassista)
   - ATTESA (⏳ Neutro)

👥 Consensus degli Agenti
   - Bull Researcher (Analista Rialzista)
   - Bear Researcher (Analista Ribassista)
   - Neutral Analyst (Analista Neutro)
   - Risk Manager (Gestore del Rischio)

📈 Dashboard Interattivo
   - Gauge della decisione
   - Grafico dei prezzi
   - Consensus visuale
   - Metriche di performance

📄 Report Scaricabili
   - PDF: Report formale
   - Excel: Dati strutturati

**COME LEGGERE I RISULTATI:**

🟢 Score positivo = Tendenza rialzista (comprare)
🔴 Score negativo = Tendenza ribassista (vendere)
⚪ Score ~0 = Mercato neutro (aspettare)

**NOTE IMPORTANTI:**

⚠️ Questo sistema è uno strumento di analisi.
   Consulta sempre un esperto prima di fare trading.

🔑 API Keys richieste:
   - OpenAI per LLM
   - Alpha Vantage (opzionale, altrimenti usa yfinance)

💡 Migliori risultati con dati storici di 6+ mesi
    """
    
    await cl.Message(content=help_text).send()


async def show_assets():
    """Mostra asset disponibili"""
    assets_text = """
📊 **ASSET SUPPORTATI**

TradingAgents supporta qualsiasi ticker disponibile su yFinance:

**Top Titoli NASDAQ:**
- NVDA - Nvidia
- AAPL - Apple
- MSFT - Microsoft
- TSLA - Tesla
- META - Meta Platforms
- AMZN - Amazon
- GOOGL - Alphabet
- AMD - AMD

**Top Titoli S&P 500:**
- JPM - JP Morgan
- V - Visa
- JNJ - Johnson & Johnson
- PG - Procter & Gamble
- UNH - UnitedHealth

**Criptovalute (su yFinance):**
- BTC-USD - Bitcoin
- ETH-USD - Ethereum
- ADA-USD - Cardano

**ETF e Indici:**
- QQQ - Nasdaq 100
- SPY - S&P 500
- VTI - Total Market
- XOM - Exxon Mobil

**Puoi analizzare qualsiasi simbolo disponibile su yFinance!**

Prova con: `ANALIZZA [TICKER]`
    """
    
    await cl.Message(content=assets_text).send()


async def analyze_stock(user_input: str):
    """Esegui analisi completa di un titolo"""
    
    # Estrai ticker e data
    parts = user_input.split()
    
    if len(parts) < 2:
        await cl.Message(
            content="❌ Formato non corretto!\n\nUso: `ANALIZZA <TICKER> [DATA]`\n\nEsempio: `ANALIZZA NVDA 2024-05-10`"
        ).send()
        return
    
    ticker = parts[1].upper()
    date = parts[2] if len(parts) > 2 else datetime.now().strftime("%Y-%m-%d")
    
    # Messaggio di processing
    await cl.Message(
        content=f"⏳ Analizzando {ticker} per la data {date}...\n\n🔄 Caricamento dati..."
    ).send()
    
    try:
        # Esegui analisi
        await cl.Message(
            content=f"🔄 Esecuzione agenti trading..."
        ).send()
        
        _, decision = ta.propagate(ticker, date)
        
        # Estrai informazioni dalla decisione
        decision_score = extract_decision_score(decision)
        sentiment = extract_sentiment(decision)
        
        # Messaggio completamento
        await cl.Message(
            content=f"✅ Analisi completata! Generazione report e dashboard..."
        ).send()
        
        # Genera dashboard
        decision_fig = dashboard_gen.create_decision_gauge(decision_score, sentiment)
        sentiment_breakdown = {
            "Rialzista": decision_score,
            "Neutro": 1 - abs(decision_score),
            "Ribassista": -decision_score if decision_score < 0 else 0
        }
        sentiment_fig = dashboard_gen.create_sentiment_breakdown(sentiment_breakdown)
        
        dashboard_path = dashboard_gen.create_dashboard_html(
            ticker=ticker,
            decision_fig=decision_fig,
            sentiment_fig=sentiment_fig,
            filename=f"dashboard_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        
        # Genera report
        analysis_data = {
            "Ticker": ticker,
            "Data Analisi": date,
            "Decision Score": round(decision_score, 3),
            "Sentiment": sentiment
        }
        
        pdf_path, excel_path = report_gen.generate_both_reports(
            ticker=ticker,
            date=date,
            decision=decision,
            analysis_data=analysis_data
        )
        
        # Crea messaggio finale
        result_text = f"""
✅ **ANALISI COMPLETATA** per `{ticker}`

📊 **DECISIONE TRADING:**
"""
        
        # Emoji decisione
        if decision_score > 0.5:
            result_text += f"💚 **ACQUISTO CONSIGLIATO** (Score: +{decision_score:.1%})"
        elif decision_score < -0.5:
            result_text += f"❌ **VENDITA CONSIGLIATA** (Score: {decision_score:.1%})"
        else:
            result_text += f"⏳ **ATTESA/NEUTRO** (Score: {decision_score:.1%})"
        
        result_text += f"""

👥 **CONSENSUS AGENTI:**
```
Sentiment Complessivo: {sentiment}
```

📈 **ANALISI DETTAGLIATA:**
```json
{str(decision)[:500]}...
```

📁 **FILE GENERATI:**
✅ Dashboard HTML
✅ Report PDF
✅ Dati Excel

Usa i pulsanti in basso per scaricare i report!
        """
        
        await cl.Message(content=result_text).send()
        
        # Carica file
        with open(dashboard_path, "rb") as f:
            dashboard_data = f.read()
        
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        with open(excel_path, "rb") as f:
            excel_data = f.read()
        
        # Invia file
        await cl.Message(
            content=f"📊 Dashboard Interattivo per {ticker}",
            elements=[
                cl.File(
                    name=Path(dashboard_path).name,
                    content=dashboard_data,
                    mime="text/html"
                )
            ]
        ).send()
        
        await cl.Message(
            content=f"📄 Report PDF per {ticker}",
            elements=[
                cl.File(
                    name=Path(pdf_path).name,
                    content=pdf_data,
                    mime="application/pdf"
                )
            ]
        ).send()
        
        await cl.Message(
            content=f"📊 Dati Excel per {ticker}",
            elements=[
                cl.File(
                    name=Path(excel_path).name,
                    content=excel_data,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            ]
        ).send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ **Errore durante l'analisi:**\n\n```\n{str(e)}\n```\n\nProva con un ticker diverso o controlla la connessione internet."
        ).send()


def extract_decision_score(decision: Any) -> float:
    """Estrai score dalla decisione"""
    try:
        decision_str = str(decision).lower()
        
        if "buy" in decision_str or "acquista" in decision_str or "rialzista" in decision_str:
            return 0.8
        elif "sell" in decision_str or "vendi" in decision_str or "ribassista" in decision_str:
            return -0.8
        else:
            return 0.0
    except:
        return 0.0


def extract_sentiment(decision: Any) -> str:
    """Estrai sentiment dalla decisione"""
    score = extract_decision_score(decision)
    
    if score > 0.5:
        return "🟢 Rialzista"
    elif score < -0.5:
        return "🔴 Ribassista"
    else:
        return "⚪ Neutro"


if __name__ == "__main__":
    cl.run()
