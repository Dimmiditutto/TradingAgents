"""
TradingAgents - App Web Interattiva con Chainlit
Interfaccia completa con Dashboard, Report e Grafici
"""

import sys
import os
from pathlib import Path

# Aggiungi parent directory al PYTHONPATH per trovare i moduli
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import chainlit as cl
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Verifica che almeno una API key sia configurata
api_key_openai = os.getenv("OPENAI_API_KEY")
api_key_anthropic = os.getenv("ANTHROPIC_API_KEY")
api_key_google = os.getenv("GOOGLE_API_KEY")

if not any([api_key_openai, api_key_anthropic, api_key_google]):
    print("\n" + "=" * 80)
    print("❌ ERRORE: Nessuna API key configurata!")
    print("=" * 80)
    print("\nPer usare TradingAgents, devi configurare almeno una API key.")
    print("\n📖 Leggi il file: SETUP_API_KEYS.md")
    print("\nPassi rapidi:")
    print("  1. Vai a https://platform.openai.com/api-keys")
    print("  2. Genera una API key")
    print("  3. Apri /workspaces/TradingAgents/web/.env")
    print("  4. Aggiungi: OPENAI_API_KEY=sk-...")
    print("  5. Salva il file")
    print("  6. Riavvia Chainlit")
    print("\n" + "=" * 80 + "\n")
    # Non voglio crashare la app, lascia che l'utente la avvii comunque
    # e poi veda il messaggio di errore quando fa il primo comando

# Import TradingAgents - LAZY LOAD
# DO NOT import heavy modules here!
# We'll import them only when needed (on first command)

# Placeholder for lazy-loaded config
DEFAULT_CONFIG = {}

# Placeholder for lazy-loaded classes
TradingAgentsGraph = None
ReportGenerator = None
DashboardGenerator = None

# Import della configurazione Chainlit - LAZY LOAD (don't import here!)
# from chainlit_config import collect_parameters

# Configurazione - usa lazy loading
config = DEFAULT_CONFIG.copy() if DEFAULT_CONFIG else {}
if not config:
    config = {
        "data_vendors": {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "yfinance",
            "news_data": "yfinance",
        }
    }
else:
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }

# Inizializza generatori - lazily
report_gen = None
dashboard_gen = None

def get_report_gen():
    """Lazy load ReportGenerator only when needed"""
    global report_gen
    if report_gen is None:
        try:
            from tradingagents.utils.report_generator import ReportGenerator as RG
            report_gen = RG(output_dir="./reports")
        except Exception as e:
            import traceback
            print(f"⚠️ Error loading ReportGenerator: {e}\n{traceback.format_exc()}")
            return None
    return report_gen

def get_dashboard_gen():
    """Lazy load DashboardGenerator only when needed"""
    global dashboard_gen
    if dashboard_gen is None:
        try:
            from tradingagents.utils.dashboard import DashboardGenerator as DG
            dashboard_gen = DG(output_dir="./dashboards")
        except Exception as e:
            import traceback
            print(f"⚠️ Error loading DashboardGenerator: {e}\n{traceback.format_exc()}")
            return None
    return dashboard_gen

# Istanza globale TradingAgents - lazy loading
ta = None
user_config = None  # Configurazione dell'utente
last_error = None  # Track last error for debugging

def get_ta():
    """Lazy load TradingAgentsGraph only when needed"""
    global ta, config, last_error
    if ta is None:
        try:
            # Ensure local package paths are available (avoid shadowed installs)
            local_root = Path(__file__).parent.parent
            alt_root = local_root / "TradingAgents"
            for path in (local_root, alt_root):
                if path.exists() and str(path) not in sys.path:
                    sys.path.insert(0, str(path))

            # Verify API keys are available
            openai_key = os.getenv("OPENAI_API_KEY")
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            google_key = os.getenv("GOOGLE_API_KEY")
            
            if not any([openai_key, anthropic_key, google_key]):
                last_error = "No API keys found in environment"
                print("❌ No API keys available. Check .env file.")
                return None
            
            # Lazy load config if needed - check for essential keys
            if "project_dir" not in config:
                from tradingagents.default_config import DEFAULT_CONFIG as DC
                # Start fresh with DEFAULT_CONFIG and preserve data_vendors
                vendors = config.get("data_vendors", {})
                config.clear()
                config.update(DC)
                if vendors:
                    config["data_vendors"] = vendors
            
            # Ensure API keys info in config
            config["api_keys_available"] = {
                "openai": openai_key is not None,
                "anthropic": anthropic_key is not None,
                "google": google_key is not None,
            }
            
            print(f"🔑 Using {config.get('llm_provider', 'openai')} provider")
            
            # Now load TradingAgentsGraph
            from tradingagents.graph.trading_graph import TradingAgentsGraph as TAG
            ta = TAG(debug=False, config=config)
            last_error = None  # Clear error on success
            print("✅ TradingAgentsGraph loaded successfully")
        except Exception as e:
            import traceback
            last_error = str(e)
            error_msg = f"⚠️ Error loading TradingAgentsGraph: {e}\n{traceback.format_exc()}"
            print(error_msg)
            return None
    return ta


async def get_collect_parameters():
    """Lazy load chainlit_config module and get collect_parameters function"""
    from chainlit_config import collect_parameters
    return await collect_parameters()



@cl.on_chat_start
async def start():
    """Inizializzazione dell'app"""
    global ta, user_config
    
    # Lazy initialize on first use
    # ta = get_ta()  # Don't load yet
    
    # Messaggio di benvenuto
    welcome_msg = """
🚀 **Benvenuto in TradingAgents!**

Sistema automatico di analisi trading con intelligenza artificiale multi-agente.

📚 **Come usarlo:**

*Opzione 1: Configurazione Guidata*
- Digita: `CONFIGURA` per il setup completo con selezione interattiva dei parametri

*Opzione 2: Comando Rapido*
- Digita: `ANALIZZA <TICKER> [DATA]` per analisi rapida con parametri di default

**Esempi:**
- `CONFIGURA` (setup completo)
- `ANALIZZA NVDA` (ultimo giorno con parametri di default)
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
    """
    
    await cl.Message(content=welcome_msg.strip()).send()


@cl.on_message
async def main(message: cl.Message):
    """Gestisci i messaggi dell'utente"""
    global ta, user_config
    
    user_input = message.content.strip().upper()
    
    try:
        # Comando CONFIGURA - Setup guidato
        if user_input == "CONFIGURA" or user_input == "SETUP":
            user_config = await get_collect_parameters()
            
            # Aggiorna la config globale con i parametri dell'utente
            ta_config = DEFAULT_CONFIG.copy() if DEFAULT_CONFIG else {}
            ta_config["max_debate_rounds"] = user_config["research_depth"]
            ta_config["max_risk_discuss_rounds"] = user_config["research_depth"]
            ta_config["quick_think_llm"] = user_config["shallow_thinker"]
            ta_config["deep_think_llm"] = user_config["deep_thinker"]
            ta_config["llm_provider"] = user_config["llm_provider"]
            ta_config["backend_url"] = user_config["backend_url"]
            
            # Update global config for next ta initialization
            config.update(ta_config)
            
            # Force reset of ta so it gets recreated with new config on next use
            ta = None
            
            await cl.Message(
                content="""
✅ **Configuration saved!**

Ora puoi eseguire analisi usando:
- `ANALIZZA <TICKER>` - usa i parametri configurati
- `ANALIZZA <TICKER> <DATA>` - specifica anche la data
                """
            ).send()
            return
        
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
- `CONFIGURA` - Configurazione guidata dei parametri
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

1️⃣ CONFIGURA (o SETUP)
   Configurazione guidata con selezione interattiva:
   ✓ Seleziona gli analisti
   ✓ Scegli la profondità della ricerca
   ✓ Configura il provider LLM
   ✓ Seleziona i modelli di thinking
   
   Usa questo comando per personalizzare completamente l'analisi!

2️⃣ ANALIZZA <TICKER> [DATA]
   Esegue analisi completa di un titolo
   - TICKER: simbolo del titolo (es. NVDA, AAPL)
   - DATA: opzionale, formato YYYY-MM-DD
   
   Esempio: `ANALIZZA NVDA 2024-05-10`
   
   💡 Se hai usato CONFIGURA, verranno usati i tuoi parametri
   📌 Altrimenti vengono usati parametri di default

3️⃣ LISTA
   Mostra i principali asset su cui puoi fare analisi

4️⃣ AIUTO
   Mostra questa guida

**WORKFLOW CONSIGLIATO:**

1. Digita `CONFIGURA` per il setup iniziale
2. Rispondi alle domande sulla configurazione
3. Usa `ANALIZZA TICKER` per eseguire l'analisi
4. Scarica report e dashboard quando terminata

**COSA RICEVI DA UN'ANALISI:**

📊 Decisione Trading
   - ACQUISTO (💚 Rialzista)
   - VENDITA (❌ Ribassista)
   - ATTESA (⏳ Neutro)

👥 Consensus degli Agenti
   - Bull Researcher (Analista Rialzista)
   - Bear Researcher (Analista Ribassista)
   - Neutral Analyst (Analista Neutro)
   - Risk Managers (Gestioni Risk diversi)

📈 Dashboard Interattivo
   - Gauge della decisione
   - Grafico dei prezzi
   - Consensus visuale
   - Metriche di performance

📄 Report Scaricabili
   - PDF: Report formale completo
   - Excel: Dati strutturati per analisi ulteriore

**COME LEGGERE I RISULTATI:**

🟢 Score positivo = Tendenza rialzista (comprare)
🔴 Score negativo = Tendenza ribassista (vendere)
⚪ Score ~0 = Mercato neutro (aspettare)

**NOTE IMPORTANTI:**

⚠️ Questo sistema è uno strumento di analisi.
   Consulta sempre un esperto prima di fare trading.

🔑 API Keys richieste:
   - OpenAI per LLM (o altro provider configurato)
   - Alpha Vantage (opzionale, altrimenti usa yfinance)

💡 Migliori risultati con dati storici di 6+ mesi

🎯 Suggerimento: Inizia con CONFIGURA per ottenere il massimo!
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
    global ta, user_config
    
    # Estrai ticker e data
    parts = user_input.split()
    
    if len(parts) < 2:
        await cl.Message(
            content="❌ Formato non corretto!\n\nUso: `ANALIZZA <TICKER> [DATA]`\n\nEsempio: `ANALIZZA NVDA 2024-05-10`"
        ).send()
        return
    
    ticker = parts[1].upper()
    date = parts[2] if len(parts) > 2 else datetime.now().strftime("%Y-%m-%d")
    
    # Se non è stata fatto il setup, mostralo
    if user_config is None:
        await cl.Message(
            content="""⚠️ **No custom configuration found**

Stai utilizzando i parametri di default. Per personalizzare l'analisi, digita:
- `CONFIGURA` - per il setup guidato completo
            """
        ).send()
    
    # Messaggio di processing
    await cl.Message(
        content=f"⏳ Analizzando {ticker} per la data {date}...\n\n🔄 Caricamento dati..."
    ).send()
    
    try:
        # Esegui analisi
        await cl.Message(
            content=f"🔄 Esecuzione agenti trading..."
        ).send()
        
        await cl.Message(
            content=f"⏳ Caricamento TradingAgentsGraph (prima volta: 10-20 secondi)..."
        ).send()
        
        trading_graph = get_ta()
        if trading_graph is None:
            # Show specific error if available
            error_detail = f"\n\n**Errore specifico:** `{last_error}`" if last_error else ""
            
            error_msg = f"""❌ Errore durante il caricamento di TradingAgentsGraph.{error_detail}

**Possibili cause:**
1. Import fallito - controlla che tutti i moduli siano presenti
2. Problema di configurazione - verifica le API keys nel .env
3. Dipendenze mancanti - controlla requirements.txt

**Debug:**
Esegui questo comando nel terminale per vedere l'errore dettagliato:
```bash
cd /workspaces/TradingAgents/web
python debug_import.py
```

Controlla anche i log del server per il traceback completo."""
            await cl.Message(content=error_msg).send()
            return
        
        _, decision = trading_graph.propagate(ticker, date)
        
        # Estrai informazioni dalla decisione
        decision_score = extract_decision_score(decision)
        sentiment = extract_sentiment(decision)
        
        # Messaggio completamento
        await cl.Message(
            content=f"✅ Analisi completata! Generazione report e dashboard..."
        ).send()
        
        # Genera dashboard
        dash_gen = get_dashboard_gen()
        if dash_gen is None:
            await cl.Message(
                content="⚠️ Dashboard generator non disponibile"
            ).send()
            return
            
        decision_fig = dash_gen.create_decision_gauge(decision_score, sentiment)
        sentiment_breakdown = {
            "Rialzista": decision_score,
            "Neutro": 1 - abs(decision_score),
            "Ribassista": -decision_score if decision_score < 0 else 0
        }
        sentiment_fig = dash_gen.create_sentiment_breakdown(sentiment_breakdown)
        
        dashboard_path = dash_gen.create_dashboard_html(
            ticker=ticker,
            decision_fig=decision_fig,
            sentiment_fig=sentiment_fig,
            filename=f"dashboard_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        
        # Genera report
        rep_gen = get_report_gen()
        if rep_gen is None:
            await cl.Message(
                content="⚠️ Report generator non disponibile"
            ).send()
            return
            
        analysis_data = {
            "Ticker": ticker,
            "Data Analisi": date,
            "Decision Score": round(decision_score, 3),
            "Sentiment": sentiment
        }
        
        pdf_path, excel_path = rep_gen.generate_both_reports(
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
