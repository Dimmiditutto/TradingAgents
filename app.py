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

# ========== HELPER FUNCTIONS ==========

# Traduzioni italiane per le sezioni
SECTION_TRANSLATIONS = {
    "market_report": "📈 Analisi Tecnica",
    "sentiment_report": "💬 Sentimento Social Media",
    "news_report": "📰 Analisi Notizie",
    "fundamentals_report": "💼 Analisi Fondamentali",
    "investment_plan": "🔬 Decisione Team Ricerca",
    "trader_investment_plan": "💹 Piano del Trader",
    "final_trade_decision": "🎯 Decisione Finale Portfolio Manager"
}

AGENT_NAMES_IT = {
    "Market Analyst": "Analista Tecnico",
    "Social Analyst": "Analista Social",
    "News Analyst": "Analista Notizie",
    "Fundamentals Analyst": "Analista Fondamentali",
    "Bull Researcher": "Ricercatore Rialzista",
    "Bear Researcher": "Ricercatore Ribassista",
    "Research Manager": "Manager Ricerca",
    "Trader": "Trader",
    "Aggressive Analyst": "Analista Aggressivo",
    "Conservative Analyst": "Analista Conservativo",
    "Neutral Analyst": "Analista Neutrale",
    "Portfolio Manager": "Portfolio Manager"
}

async def stream_analysis_with_updates(graph, ticker: str, date: str, progress_msg):
    """
    Stream analysis with real-time progressive updates and progress bar.
    Shows each report section as soon as it's completed with live progress tracking.
    """
    import asyncio
    from queue import Queue
    import time
    
    # Initialize state
    init_agent_state = graph.propagator.create_initial_state(ticker, date)
    args = graph.propagator.get_graph_args(callbacks=[])
    
    # Queue for thread-safe communication between streaming thread and async loop
    report_queue = Queue()
    streaming_done = False
    
    # Run streaming in executor thread
    loop = asyncio.get_event_loop()
    
    def stream_graph_and_queue():
        """Synchronous streaming that puts reports into queue"""
        nonlocal streaming_done
        reports_data = {}
        trace = []
        last_keys = set()
        
        try:
            for chunk in graph.graph.stream(init_agent_state, **args):
                trace.append(chunk)
                
                # Extract all available reports from current chunk
                reports_to_send = {}
                
                # Check each report type
                if "market_report" in chunk and chunk["market_report"] and "market_report" not in reports_data:
                    reports_data["market_report"] = chunk["market_report"]
                    reports_to_send["market_report"] = chunk["market_report"]
                    
                if "sentiment_report" in chunk and chunk["sentiment_report"] and "sentiment_report" not in reports_data:
                    reports_data["sentiment_report"] = chunk["sentiment_report"]
                    reports_to_send["sentiment_report"] = chunk["sentiment_report"]
                    
                if "news_report" in chunk and chunk["news_report"] and "news_report" not in reports_data:
                    reports_data["news_report"] = chunk["news_report"]
                    reports_to_send["news_report"] = chunk["news_report"]
                    
                if "fundamentals_report" in chunk and chunk["fundamentals_report"] and "fundamentals_report" not in reports_data:
                    reports_data["fundamentals_report"] = chunk["fundamentals_report"]
                    reports_to_send["fundamentals_report"] = chunk["fundamentals_report"]
                
                # Check for research team decision
                if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
                    debate = chunk["investment_debate_state"]
                    if debate.get("judge_decision") and "investment_plan" not in reports_data:
                        reports_data["investment_plan"] = debate["judge_decision"]
                        reports_to_send["investment_plan"] = debate["judge_decision"]
                
                # Check for trader plan
                if "trader_investment_plan" in chunk and chunk["trader_investment_plan"] and "trader_investment_plan" not in reports_data:
                    reports_data["trader_investment_plan"] = chunk["trader_investment_plan"]
                    reports_to_send["trader_investment_plan"] = chunk["trader_investment_plan"]
                
                # Check for final decision
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk = chunk["risk_debate_state"]
                    if risk.get("judge_decision") and "final_trade_decision" not in reports_data:
                        reports_data["final_trade_decision"] = risk["judge_decision"]
                        reports_to_send["final_trade_decision"] = risk["judge_decision"]
                
                # Queue any new reports
                if reports_to_send:
                    for key, content in reports_to_send.items():
                        report_queue.put(("report", key, content, len(reports_data)))
            
            # Signal end of streaming
            final_state = trace[-1] if trace else {}
            decision = graph.process_signal(final_state.get("final_trade_decision", ""))
            report_queue.put(("done", final_state, decision, reports_data))
            
        except Exception as e:
            report_queue.put(("error", str(e)))
        finally:
            streaming_done = True
    
    # Start streaming in thread
    future = loop.run_in_executor(None, stream_graph_and_queue)
    
    # Remove progress message and start showing real updates
    await progress_msg.remove()
    
    # Create progress indicator message
    progress_text = await cl.Message(
        content="🔄 **Analisi in corso...**\n\n"
                "⏳ Gli agenti stanno analizzando. Vedrai i report man mano che vengono completati.\n\n"
                "_Questo potrebbe richiedere 30-90 secondi..._"
    ).send()
    
    # Consumer loop: Process reports as they arrive
    reports_data = {}
    final_state = None
    decision = None
    completed_sections = []
    
    while True:
        try:
            # Check queue without blocking
            if not report_queue.empty():
                item = report_queue.get(timeout=0.5)
                
                if item[0] == "report":
                    _, section_key, content, total_count = item
                    reports_data[section_key] = content
                    completed_sections.append(section_key)
                    
                    # Remove progress indicator (will add new one if more sections coming)
                    try:
                        await progress_text.remove()
                    except:
                        pass
                    
                    # Translate and send the completed report immediately
                    section_title = SECTION_TRANSLATIONS.get(section_key, section_key)
                    
                    # Translate the report to Italian
                    translated_content = await translate_to_italian(content[:2500])
                    
                    # Send the translated report
                    await cl.Message(
                        content=f"## {section_title}\n\n{translated_content}"
                    ).send()
                    
                    # Update progress with what's completed
                    progress_text = await cl.Message(
                        content=f"🔄 **Analisi in corso...**\n\n"
                                f"✅ Completati: {len(completed_sections)}/{7}\n\n"
                                + "\n".join([f"  ✓ {SECTION_TRANSLATIONS.get(s, s)}" for s in completed_sections]) +
                                f"\n\n_Agenti in lavoro..._"
                    ).send()
                    
                    await asyncio.sleep(0.5)
                    
                elif item[0] == "done":
                    _, final_state, decision, reports_data = item
                    break
                    
                elif item[0] == "error":
                    _, error_msg = item
                    try:
                        await progress_text.remove()
                    except:
                        pass
                    await cl.Message(content=f"❌ Errore durante l'analisi: {error_msg}").send()
                    return None, None, {}
                    
            elif streaming_done and report_queue.empty():
                # Wait a bit more to ensure we got all items
                await asyncio.sleep(1)
                if report_queue.empty():
                    break
            else:
                # Nothing in queue yet, check again soon
                await asyncio.sleep(0.5)
                
        except Exception as e:
            # Queue timeout or other error, continue loop
            await asyncio.sleep(0.5)
            continue
    
    # Clean up progress message
    try:
        await progress_text.remove()
    except:
        pass
    
    # Send completion message
    await cl.Message(
        content=f"✅ **Analisi completata!**\n\n"
                f"✅ Generati **{len(reports_data)}** report dettagliati\n\n"
                f"🔄 _Generazione file completi in corso..._"
    ).send()
    
    await future  # Ensure thread finishes
    
    return final_state, decision, reports_data


async def translate_to_italian(text: str) -> str:
    """Translate English text to Italian using OpenAI"""
    try:
        import openai
        import os
        
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sei un traduttore esperto. Traduci il seguente testo finanziario dall'inglese all'italiano, mantenendo la terminologia tecnica appropriata."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        # If translation fails, return original with note
        return f"⚠️ _Traduzione non disponibile_\n\n{text[:300]}..."


def generate_complete_markdown_report(ticker: str, date: str, final_state: dict, decision_score: float, sentiment: str) -> str:
    """
    Generate a complete markdown report from final_state, similar to CLI's display_complete_report.
    
    Args:
        ticker: Stock ticker symbol
        date: Analysis date
        final_state: Complete state from propagate() containing all reports
        decision_score: Numerical decision score
        sentiment: Sentiment classification
        
    Returns:
        Complete markdown report as string
    """
    from datetime import datetime
    
    report_parts = []
    
    # Title and metadata
    report_parts.append(f"# 📊 TradingAgents - Analisi Completa per {ticker}")
    report_parts.append(f"**Data Analisi:** {date}")
    report_parts.append(f"**Data Generazione:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_parts.append(f"**Decisione:** {sentiment} (Score: {decision_score:.2%})")
    report_parts.append("\n---\n")
    
    # I. Analyst Team Reports
    analyst_sections = []
    
    if final_state.get("market_report"):
        analyst_sections.append("## 📈 Analisi Tecnica\n\n" + final_state["market_report"])
    
    if final_state.get("sentiment_report"):
        analyst_sections.append("## 💬 Sentimento Social Media\n\n" + final_state["sentiment_report"])
    
    if final_state.get("news_report"):
        analyst_sections.append("## 📰 Analisi Notizie\n\n" + final_state["news_report"])
    
    if final_state.get("fundamentals_report"):
        analyst_sections.append("## 💼 Analisi Fondamentali\n\n" + final_state["fundamentals_report"])
    
    if analyst_sections:
        report_parts.append("# 🎯 PARTE I: Analisi degli Analisti\n")
        report_parts.extend(analyst_sections)
        report_parts.append("\n---\n")
    
    # II. Research Team Decision
    if final_state.get("investment_debate_state"):
        debate_state = final_state["investment_debate_state"]
        report_parts.append("# 🔬 PARTE II: Decisione del Team di Ricerca\n")
        
        if debate_state.get("bull_history"):
            report_parts.append("## 🟢 Analisi Ricercatore Rialzista\n\n" + debate_state["bull_history"])
        
        if debate_state.get("bear_history"):
            report_parts.append("## 🔴 Analisi Ricercatore Ribassista\n\n" + debate_state["bear_history"])
        
        if debate_state.get("judge_decision"):
            report_parts.append("## ⚖️ Decisione Manager Ricerca\n\n" + debate_state["judge_decision"])
        
        report_parts.append("\n---\n")
    
    # III. Trading Team Plan
    if final_state.get("trader_investment_plan"):
        report_parts.append("# 💹 PARTE III: Piano del Trader\n")
        report_parts.append(final_state["trader_investment_plan"])
        report_parts.append("\n---\n")
    
    # IV. Risk Management Team Decision
    if final_state.get("risk_debate_state"):
        risk_state = final_state["risk_debate_state"]
        report_parts.append("# 🛡️ PARTE IV: Gestione del Rischio\n")
        
        if risk_state.get("aggressive_history"):
            report_parts.append("## 🔥 Analisi Analista Aggressivo\n\n" + risk_state["aggressive_history"])
        
        if risk_state.get("conservative_history"):
            report_parts.append("## 🏦 Analisi Analista Conservativo\n\n" + risk_state["conservative_history"])
        
        if risk_state.get("neutral_history"):
            report_parts.append("## ⚖️ Analisi Analista Neutrale\n\n" + risk_state["neutral_history"])
        
        report_parts.append("\n---\n")
    
    # V. Portfolio Manager Final Decision
    if final_state.get("risk_debate_state") and final_state["risk_debate_state"].get("judge_decision"):
        report_parts.append("# 🎯 PARTE V: Decisione Finale Portfolio Manager\n")
        report_parts.append(final_state["risk_debate_state"]["judge_decision"])
        report_parts.append("\n---\n")
    
    # Footer
    report_parts.append("\n---\n")
    report_parts.append("*Rapporto generato automaticamente da TradingAgents - Sistema Multi-Agente per Analisi Trading*")
    
    return "\n\n".join(report_parts)

# ========== LAZY LOADERS ==========

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

**1. CERCA un titolo:**
   `CERCA Apple` → trova il ticker AAPL
   `CERCA Tesla` → trova il ticker TSLA
   `CERCA Microsoft` → trova il ticker MSFT

**2. CONFIGURA i parametri (opzionale):**
   `CONFIGURA` → setup completo con selezione interattiva

**3. ANALIZZA un titolo:**
   `ANALIZZA NVDA` → analisi immediata con parametri default
   `ANALIZZA AAPL 2024-05-10` → con data specifica
   `LISTA` → vedi asset disponibili

**Esempi veloci:**
```
CERCA Apple
ANALIZZA AAPL
LISTA
AIUTO
```

⚙️ **L'analisi includerà:**
✅ Streaming real-time con barra di progresso
✅ Report multi-agente (Tecnica, Social, News, Fondamentale)
✅ Dibattito team di ricerca
✅ Decisione trading (BUY/SELL/HOLD)
✅ Dashboard interattivo scaricabile
✅ Report PDF e Excel

🎯 **Inizia subito:** Digita `CERCA Apple`
"""
    
    await cl.Message(content=welcome_msg).send()


@cl.on_message
async def main(message: cl.Message):
    """Handler principale per i messaggi dell'utente"""
    global ta, user_config
    
    user_input = message.content.strip().upper()
    
    try:
        # Comando CERCA - Search for ticker symbols
        if user_input.startswith("CERCA"):
            await search_ticker(user_input)
            return
        
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


async def search_ticker(user_input: str):
    """Search for ticker symbols by company name or keyword"""
    parts = user_input.split(maxsplit=1)
    if len(parts) < 2:
        await cl.Message(
            content="""❌ **Uso:** `CERCA <nome>`

**Esempi:**
- `CERCA Apple` → AAPL
- `CERCA Tesla` → TSLA
- `CERCA Microsoft` → MSFT
- `CERCA Nvidia` → NVDA
- `CERCA Gold` → GC=F"""
        ).send()
        return
    
    query = parts[1].strip()
    await cl.Message(content=f"🔍 Ricerca: **{query}**...").send()
    
    # Extended ticker mapping with Italian names
    quick_map = {
        "APPLE": ("AAPL", "Apple Inc."),
        "MSFT": ("MSFT", "Microsoft"),
        "MICROSOFT": ("MSFT", "Microsoft"),
        "GOOGLE": ("GOOGL", "Google"),
        "GOOGL": ("GOOGL", "Google"),
        "AMAZON": ("AMZN", "Amazon"),
        "AMZN": ("AMZN", "Amazon"),
        "TESLA": ("TSLA", "Tesla"),
        "TSLA": ("TSLA", "Tesla"),
        "META": ("META", "Meta Platforms"),
        "NVIDIA": ("NVDA", "Nvidia"),
        "NVDA": ("NVDA", "Nvidia"),
        "NETFLIX": ("NFLX", "Netflix"),
        "NFLX": ("NFLX", "Netflix"),
        "AMD": ("AMD", "Advanced Micro Devices"),
        "INTEL": ("INTC", "Intel"),
        "INTC": ("INTC", "Intel"),
        "IBM": ("IBM", "IBM"),
        "ORACLE": ("ORCL", "Oracle"),
        "ORCL": ("ORCL", "Oracle"),
        "CISCO": ("CSCO", "Cisco"),
        "CSCO": ("CSCO", "Cisco"),
        "S&P": ("SPY", "S&P 500"),
        "SPY": ("SPY", "S&P 500"),
        "S&P500": ("SPY", "S&P 500"),
        "NASDAQ": ("QQQ", "Nasdaq 100"),
        "QQQ": ("QQQ", "Nasdaq 100"),
        "DOW": ("DIA", "Dow Jones"),
        "DIA": ("DIA", "Dow Jones"),
        "BITCOIN": ("BTC-USD", "Bitcoin"),
        "BTC": ("BTC-USD", "Bitcoin"),
        "ETHEREUM": ("ETH-USD", "Ethereum"),
        "ETH": ("ETH-USD", "Ethereum"),
        "GOLD": ("GC=F", "Oro"),
        "ORO": ("GC=F", "Oro"),
        "GC": ("GC=F", "Oro"),
    }
    
    query_upper = query.upper()
    
    # Exact match
    if query_upper in quick_map:
        ticker, name = quick_map[query_upper]
        await cl.Message(
            content=f"""✅ **Trovato:** `{ticker}`
📊 {name}

💡 Usa: `ANALIZZA {ticker}` per l'analisi completa"""
        ).send()
    else:
        # Partial matches
        suggestions = [(k, v) for k, v in quick_map.items() if query_upper in k or query_upper in v[1].upper()]
        if suggestions:
            result = "🔍 **Risultati trovati:**\n\n"
            for _, (ticker, name) in suggestions[:8]:
                result += f"✓ `{ticker}` - {name}\n"
            result += "\n💡 Usa: `ANALIZZA <TICKER>` per l'analisi"
            await cl.Message(content=result).send()
        else:
            await cl.Message(
                content=f"""❌ **{query}** non trovato.

**Prova con questi:**
- `CERCA Apple`
- `CERCA Tesla`
- `CERCA Microsoft`
- `CERCA S&P500`
- `CERCA Bitcoin`
- `CERCA Gold`"""
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
        
        # ========== STREAMING ANALYSIS WITH PROGRESSIVE UPDATES ==========
        progress_msg = await cl.Message(
            content=f"🔄 **Analisi in corso...**\n\n⏳ _Inizializzazione workflow agenti..._"
        ).send()
        
        # Run streaming analysis with progressive updates
        import asyncio
        final_state, decision, reports_data = await stream_analysis_with_updates(
            trading_graph, ticker, date, progress_msg
        )
        
        # Estrai informazioni dalla decisione
        decision_score = extract_decision_score(decision)
        sentiment = extract_sentiment(decision)
        
        # Messaggio completamento
        await cl.Message(
            content=f"✅ Analisi completata! Generazione report completo e dashboard..."
        ).send()
        
        # ========== GENERATE COMPLETE REPORT (like CLI) ==========
        # Create report directory structure like CLI
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use absolute path based on app.py location
        web_dir = Path(__file__).parent
        report_base_dir = web_dir / "reports" / f"{ticker}_{timestamp}"
        report_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Build complete markdown report from final_state
        complete_report = generate_complete_markdown_report(ticker, date, final_state, decision_score, sentiment)
        
        # Save complete report
        complete_report_path = report_base_dir / "complete_report.md"
        with open(complete_report_path, "w", encoding="utf-8") as f:
            f.write(complete_report)
        
        # Save individual sections (like CLI does)
        sections_dir = report_base_dir / "sections"
        sections_dir.mkdir(exist_ok=True)
        
        # Save analyst reports
        if final_state.get("market_report"):
            (sections_dir / "1_market_report.md").write_text(final_state["market_report"], encoding="utf-8")
        if final_state.get("sentiment_report"):
            (sections_dir / "2_sentiment_report.md").write_text(final_state["sentiment_report"], encoding="utf-8")
        if final_state.get("news_report"):
            (sections_dir / "3_news_report.md").write_text(final_state["news_report"], encoding="utf-8")
        if final_state.get("fundamentals_report"):
            (sections_dir / "4_fundamentals_report.md").write_text(final_state["fundamentals_report"], encoding="utf-8")
        
        # Save research team reports
        if final_state.get("investment_debate_state"):
            debate_state = final_state["investment_debate_state"]
            research_dir = sections_dir / "5_research_team"
            research_dir.mkdir(exist_ok=True)
            if debate_state.get("bull_history"):
                (research_dir / "bull_researcher.md").write_text(debate_state["bull_history"], encoding="utf-8")
            if debate_state.get("bear_history"):
                (research_dir / "bear_researcher.md").write_text(debate_state["bear_history"], encoding="utf-8")
            if debate_state.get("judge_decision"):
                (research_dir / "research_manager.md").write_text(debate_state["judge_decision"], encoding="utf-8")
        
        # Save trading team report
        if final_state.get("trader_investment_plan"):
            (sections_dir / "6_trader_plan.md").write_text(final_state["trader_investment_plan"], encoding="utf-8")
        
        # Save risk management reports
        if final_state.get("risk_debate_state"):
            risk_state = final_state["risk_debate_state"]
            risk_dir = sections_dir / "7_risk_management"
            risk_dir.mkdir(exist_ok=True)
            if risk_state.get("aggressive_history"):
                (risk_dir / "aggressive_analyst.md").write_text(risk_state["aggressive_history"], encoding="utf-8")
            if risk_state.get("conservative_history"):
                (risk_dir / "conservative_analyst.md").write_text(risk_state["conservative_history"], encoding="utf-8")
            if risk_state.get("neutral_history"):
                (risk_dir / "neutral_analyst.md").write_text(risk_state["neutral_history"], encoding="utf-8")
            if risk_state.get("judge_decision"):
                (risk_dir / "portfolio_manager.md").write_text(risk_state["judge_decision"], encoding="utf-8")
        
        # ========== GENERATE DASHBOARD ==========
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
            filename=f"dashboard_{ticker}_{timestamp}.html"
        )
        
        # ========== GENERATE PDF & EXCEL REPORTS ==========
        rep_gen = get_report_gen()
        if rep_gen is None:
            await cl.Message(
                content="⚠️ Report generator non disponibile"
            ).send()
            # Continue without PDF/Excel
            pdf_path = None
            excel_path = None
        else:
            analysis_data = {
                "Ticker": ticker,
                "Data Analisi": date,
                "Decision Score": round(decision_score, 3),
                "Sentiment": sentiment
            }
            
            # Generate PDF and Excel
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
            result_text += f"\n💚 **ACQUISTO CONSIGLIATO** (Score: +{decision_score:.1%})"
        elif decision_score < -0.5:
            result_text += f"\n❌ **VENDITA CONSIGLIATA** (Score: {decision_score:.1%})"
        else:
            result_text += f"\n⚖️ **ATTESA CONSIGLIATA** (Score: {decision_score:.1%})"
        
        result_text += f"\n\n**Sentiment:** {sentiment}\n"
        
        # Count generated sections
        num_sections = len(list(sections_dir.rglob('*.md'))) if sections_dir.exists() else 0
        
        result_text += f"""
---

📂 **FILE GENERATI:**

📄 **Report Completo (Markdown):** `{report_base_dir.name}/complete_report.md`
📊 **Dashboard Interattivo (HTML):** `{Path(dashboard_path).name}`
📑 **Report PDF:** {f"`{Path(pdf_path).name}`" if pdf_path else "Non disponibile"}
📊 **Dati Excel:** {f"`{Path(excel_path).name}`" if excel_path else "Non disponibile"}

📁 ** {num_sections} sezioni individuali** salvate in: `{report_base_dir.name}/sections/`

🔍 **Il report include:**
- ✅ Analisi Tecnica, Social, Notizie, Fondamentali (tradotte in italiano)
- ✅ Dibattito team di ricerca (Bull/Bear + Manager)
- ✅ Piano del Trader
- ✅ Analisi Risk Management
- ✅ Decisione finale Portfolio Manager

💾 **Download disponibili qui sotto!**
        """
        
        await cl.Message(content=result_text).send()
        
        # Send complete report as downloadable file
        try:
            await cl.Message(
                content="📥 **Scarica il Report Completo (Markdown):**",
                elements=[
                    cl.File(
                        name=complete_report_path.name,
                        path=str(complete_report_path),
                        display="inline"
                    )
                ]
            ).send()
        except Exception as e:
            await cl.Message(content=f"⚠️ Nota: Report Markdown salvato in `{complete_report_path}`").send()
        
        # Send PDF report if generated
        if pdf_path:
            try:
                await cl.Message(
                    content="📑 **Scarica il Report PDF:**",
                    elements=[
                        cl.File(
                            name=Path(pdf_path).name,
                            path=str(pdf_path),
                            display="inline"
                        )
                    ]
                ).send()
            except Exception as e:
                await cl.Message(content=f"⚠️ Nota: Report PDF salvato in `{pdf_path}`").send()
        
        # Send Excel report if generated
        if excel_path:
            try:
                await cl.Message(
                    content="📊 **Scarica i Dati Excel:**",
                    elements=[
                        cl.File(
                            name=Path(excel_path).name,
                            path=str(excel_path),
                            display="inline"
                        )
                    ]
                ).send()
            except Exception as e:
                await cl.Message(content=f"⚠️ Nota: Dati Excel salvati in `{excel_path}`").send()
        
        # Send dashboard file
        try:
            await cl.Message(
                content="📊 **Dashboard Interattivo (HTML):**",
                elements=[
                    cl.File(
                        name=Path(dashboard_path).name,
                        path=str(dashboard_path),
                        display="inline"
                    )
                ]
            ).send()
        except Exception as e:
            await cl.Message(content=f"⚠️ Nota: Dashboard salvato in `{dashboard_path}`").send()
        
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
