"""
Esempio di LONG-TERM INVESTING (3+ mesi)
Ottimizzato per analisi fondamentale approfondita e decisioni strategiche
"""

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import INVESTING_CONFIG
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("📈 INVESTING MODE - Analisi Lungo Termine (3+ mesi)")
print("=" * 60)
print()

# Configurazione ottimizzata per investing
print("📋 Configurazione Long-Term Investing:")
print(f"  - Strategy Type: {INVESTING_CONFIG['strategy_type']}")
print(f"  - Debate Rounds: {INVESTING_CONFIG['max_debate_rounds']} (analisi strategica)")
print(f"  - Risk Rounds: {INVESTING_CONFIG['max_risk_discuss_rounds']} (risk profondo)")
print(f"  - LLM Model: {INVESTING_CONFIG['deep_think_llm']} (reasoning avanzato)")
print(f"  - Focus: Fundamentals + Long-term trends")
print()

# Opzione 1: Usa config preimpostata
ta_investing = TradingAgentsGraph(
    selected_analysts=["fundamentals", "market", "news"],  # Focus su fundamentals
    debug=True,
    config=INVESTING_CONFIG
)

# Esempio 1: Analisi long-term su blue chip
print("📊 Esempio 1: Long-Term Investing su AAPL")
print("-" * 60)

_, decision = ta_investing.propagate("AAPL", "2024-05-10")

print()
print("✅ Decisione Investment:", decision)
print()

# Esempio 2: Long-term su indice ETF
print("📊 Esempio 2: Long-Term Investing su VOO (Vanguard S&P 500)")
print("-" * 60)

_, decision_voo = ta_investing.propagate("VOO", "2024-05-10")

print()
print("✅ Decisione Investment VOO:", decision_voo)
print()

# Esempio 3: Growth stock per portfolio diversification
print("📊 Esempio 3: Growth Stock - MSFT")
print("-" * 60)

_, decision_msft = ta_investing.propagate("MSFT", "2024-05-10")

print()
print("✅ Decisione Investment MSFT:", decision_msft)
print()

# Opzione 2: Portfolio di lungo termine
print("=" * 60)
print("🏦 PORTFOLIO BUILDING - Multiple Holdings")
print("=" * 60)

portfolio_symbols = ["SPY", "QQQ", "AAPL", "MSFT", "VOO"]
portfolio_decisions = {}

print("\n📋 Analisi Portfolio Diversificato:")
print("-" * 60)

for symbol in portfolio_symbols:
    print(f"\n🔍 Analizzando {symbol}...")
    _, decision = ta_investing.propagate(symbol, "2024-05-10")
    portfolio_decisions[symbol] = decision
    print(f"  ✅ {symbol}: {decision}")

print()
print("=" * 60)
print("📊 SUMMARY PORTFOLIO:")
print("=" * 60)

buy_count = sum(1 for d in portfolio_decisions.values() if "BUY" in d.upper())
hold_count = sum(1 for d in portfolio_decisions.values() if "HOLD" in d.upper())
sell_count = sum(1 for d in portfolio_decisions.values() if "SELL" in d.upper())

print(f"""
Total Assets Analyzed: {len(portfolio_symbols)}
  🟢 BUY Signals:  {buy_count}
  🟡 HOLD Signals: {hold_count}
  🔴 SELL Signals: {sell_count}

Raccomandazioni:
""")

for symbol, decision in portfolio_decisions.items():
    print(f"  - {symbol}: {decision}")

print()
print("=" * 60)
print("📈 INVESTING INDICATORS DISPONIBILI:")
print("=" * 60)
print("""
LONG-TERM TREND:
  - 200 SMA: Trend secolare (sopra = bull market, sotto = bear)
  - 50 SMA: Trend medio termine per timing tattico
  - MACD Monthly: Crossover mensili = cambio ciclico

FUNDAMENTAL METRICS:
  - Balance Sheet: Salute finanziaria
  - Cash Flow: Liquidità e sostenibilità
  - Income Statement: Redditività
  - Company Overview: Settore, capitalizzazione, dividendi

VALUATION:
  - Bollinger Bands: Valutazione relativa vs storico
  - RSI Monthly: Zone di accumulo (<30) o distribuzione (>70)

RISK ASSESSMENT:
  - ATR: Volatilità per position sizing
  - Long-term volatility: Beta vs indice

STRATEGIA CONSIGLIATA:
1. Analisi fundamentals (bilanci, flussi di cassa)
2. Conferma trend con 200 SMA
3. Valutazione relativa con Bollinger Bands
4. Entry in zone di accumulo (RSI < 30 su monthly)
5. Holding: 6+ mesi
6. Rebalancing: Trimestrale
""")

print()
print("=" * 60)
print("💡 TIPS PER LONG-TERM INVESTING:")
print("=" * 60)
print("""
✅ Quando investire long-term:
  - Fundamentals solidi (balance sheet, cash flow positivi)
  - Prezzo sopra 200 SMA (bull market)
  - RSI monthly < 40 (zona accumulo)
  - Settore in crescita secolare
  - Management di qualità

❌ Quando evitare:
  - Fundamentals deboli (debito alto, cash flow negativo)
  - Prezzo sotto 200 SMA (bear market)
  - RSI monthly > 70 (zona distribuzione)
  - Settore in declino strutturale

⏱️ Holding Period: 6+ mesi (ottimale 1-3 anni)
🎯 Target: +10-30% annuo
🛑 Stop Loss: Non rigido; rivaluta quarterly
💰 Position Sizing: Basato su ATR e portfolio allocation
🔄 Rebalancing: Trimestrale o semestrale

DIVERSIFICAZIONE CONSIGLIATA:
  - 40% Large Cap (SPY, VOO)
  - 30% Growth (QQQ, tech stocks)
  - 20% Value (dividendi, blue chips)
  - 10% International/Bonds

METRICHE DI VALUTAZIONE:
  - P/E Ratio: vs storico e vs settore
  - PEG Ratio: crescita futura
  - Dividend Yield: income steady
  - ROE/ROA: efficienza gestionale
""")
