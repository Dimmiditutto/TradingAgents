"""
Esempio di SWING TRADING (2-10 giorni)
Ottimizzato per decisioni rapide con analisi tecnica approfondita
"""

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import SWING_CONFIG
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🎯 SWING TRADING MODE - Analisi Breve Termine (2-10 giorni)")
print("=" * 60)
print()

# Configurazione ottimizzata per swing trading
print("📋 Configurazione Swing Trading:")
print(f"  - Strategy Type: {SWING_CONFIG['strategy_type']}")
print(f"  - Debate Rounds: {SWING_CONFIG['max_debate_rounds']} (analisi approfondita)")
print(f"  - Risk Rounds: {SWING_CONFIG['max_risk_discuss_rounds']}")
print(f"  - LLM Model: {SWING_CONFIG['deep_think_llm']} (velocità)")
print(f"  - Analysts: TUTTI (market, social, news, fundamentals)")
print()

# Opzione 1: Usa config preimpostata
ta_swing = TradingAgentsGraph(
    selected_analysts=["market", "social", "news", "fundamentals"],
    debug=True,
    config=SWING_CONFIG
)

# Esempio 1: Analisi swing trading su titolo tech
print("📊 Esempio 1: Swing Trading su NVDA")
print("-" * 60)

_, decision = ta_swing.propagate("NVDA", "2024-05-10")

print()
print("✅ Decisione Swing Trading:", decision)
print()

# Esempio 2: Swing trading su indice
print("📊 Esempio 2: Swing Trading su SPY (S&P 500 ETF)")
print("-" * 60)

_, decision_spy = ta_swing.propagate("SPY", "2024-05-10")

print()
print("✅ Decisione Swing Trading SPY:", decision_spy)
print()

# Opzione 2: Personalizza ulteriormente il config
print("=" * 60)
print("🔧 Personalizzazione Avanzata Swing")
print("=" * 60)

custom_swing_config = SWING_CONFIG.copy()
custom_swing_config["max_debate_rounds"] = 5  # Ancora più analisi
custom_swing_config["data_vendors"]["news_data"] = "yfinance"  # Free news

ta_custom_swing = TradingAgentsGraph(
    selected_analysts=["market", "social", "news"],  # Solo analisti tecnici
    debug=True,
    config=custom_swing_config
)

print()
print("📊 Esempio 3: Swing Personalizzato (solo tecnico + sentiment)")
print("-" * 60)

_, decision_custom = ta_custom_swing.propagate("TSLA", "2024-05-10")

print()
print("✅ Decisione Swing Personalizzata:", decision_custom)
print()

print("=" * 60)
print("📈 SWING TRADING INDICATORS DISPONIBILI:")
print("=" * 60)
print("""
FORZA DEL TREND:
  - ADX (Average Directional Index): > 25 = trend forte
  - +DI/-DI: Direzione del trend
  - ER (Efficiency Ratio): > 0.5 = trend efficiente

DIREZIONE DEL TREND:
  - SuperTrend: Support/resistance dinamico
  - Linear Regression: Regressione lineare + slope + R²
  - Ichimoku Cloud: 5 componenti (Tenkan, Kijun, Senkou A/B, Chikou)

MOMENTUM:
  - TSI (True Strength Index): Momentum double-smoothed
  - TSI Signal: Crossover per entry/exit
  - RSI: Classico overbought/oversold
  - MACD: Momentum via EMA differences

ENTRY/EXIT TIMING:
  - Bollinger Bands: Volatility bands
  - ATR: Stop-loss placement
  - Volume: VWMA per conferma

STRATEGIA CONSIGLIATA:
1. Verifica ADX > 25 (trend forte)
2. Conferma direzione con SuperTrend + Ichimoku
3. Entry con RSI + TSI alignment
4. Stop-loss a 1.5-2x ATR
5. Target: +2-5% per swing
""")

print()
print("=" * 60)
print("💡 TIPS PER SWING TRADING:")
print("=" * 60)
print("""
✅ Quando usare swing:
  - Trend forte (ADX > 25)
  - ER > 0.5 (trend pulito, non noisy)
  - Tutti gli indicatori allineati nella stessa direzione
  - Volume in crescita

❌ Quando evitare swing:
  - ADX < 20 (mercato laterale)
  - ER < 0.3 (troppo noise)
  - Indicatori contrastanti
  - Bassa volatilità (ATR basso)

⏱️ Holding Period: 2-10 giorni (media 5-7 giorni)
🎯 Target: +2-5% per trade
🛑 Stop Loss: 1.5-2x ATR sotto entry
""")
