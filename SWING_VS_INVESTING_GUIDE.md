# 🎯 Trading Agents: Swing vs Investing Mode

## 📋 Panoramica

Il framework TradingAgents ora supporta **due modalità operative distinte**:

1. **🎯 SWING TRADING** (2-10 giorni) - Ottimizzato per trading breve termine
2. **📈 INVESTING** (3+ mesi) - Ottimizzato per investimenti lungo termine

---

## 🚀 Quick Start

### Swing Trading (Raccomandato per trade rapidi)

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import SWING_CONFIG

# Usa configurazione preottimizzata per swing
ta = TradingAgentsGraph(
    selected_analysts=["market", "social", "news", "fundamentals"],
    config=SWING_CONFIG
)

# Analizza un titolo
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)  # Output: "BUY/SELL/HOLD" + analisi dettagliata
```

### Long-Term Investing

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import INVESTING_CONFIG

# Usa configurazione preottimizzata per investing
ta = TradingAgentsGraph(
    selected_analysts=["fundamentals", "market", "news"],
    config=INVESTING_CONFIG
)

# Analizza per holding lungo termine
_, decision = ta.propagate("AAPL", "2024-05-10")
```

---

## 🔧 Differenze Chiave tra Swing e Investing

| Parametro | Swing Trading | Investing |
|-----------|--------------|-----------|
| **Holding Period** | 2-10 giorni | 3+ mesi |
| **Debate Rounds** | 3 (approfondito) | 5 (strategico) |
| **Risk Analysis** | 2 rounds | 3 rounds |
| **LLM Model** | gpt-5-mini (veloce) | gpt-5.2 (profondo) |
| **Focus** | Tecnico + Sentiment | Fundamentals + Trend |
| **Indicatori Chiave** | ADX, SuperTrend, TSI | 200 SMA, Fundamentals |
| **Target Profit** | +2-5% per trade | +10-30% annuo |
| **Stop Loss** | 1.5-2x ATR | Rivalutazione quarterly |

---

## 📊 Nuovi Indicatori Tecnici per Swing Trading

### Forza del Trend (Trend Strength)

1. **ADX (Average Directional Index)**
   - ADX > 25 = trend forte (buono per swing)
   - ADX < 20 = mercato laterale (evitare)
   - Combina con +DI/-DI per direzione

2. **+DI / -DI (Directional Indicators)**
   - +DI > -DI = uptrend
   - -DI > +DI = downtrend

3. **ER (Efficiency Ratio)**
   - ER vicino a 1 = trend direzionale forte
   - ER vicino a 0 = mercato noisy/laterale
   - Filtrare swing: solo quando ER > 0.5

### Direzione del Trend (Trend Direction)

4. **SuperTrend**
   - Support/resistance dinamico basato su ATR
   - Prezzo sopra = uptrend, sotto = downtrend
   - Pochi falsi segnali in trending markets

5. **Linear Regression**
   - Linea di regressione a 20 periodi
   - Slope > 0 = uptrend, < 0 = downtrend
   - R² vicino a 1 = trend consistente

6. **Ichimoku Cloud** (5 componenti)
   - Tenkan-sen: Linea conversione (9 periodi)
   - Kijun-sen: Linea base (26 periodi)
   - Senkou Span A/B: Cloud boundaries
   - Chikou Span: Lagging span
   - Prezzo sopra cloud = bullish

### Momentum

7. **TSI (True Strength Index)**
   - Momentum double-smoothed
   - TSI > 0 = bullish, < 0 = bearish
   - Crossover con signal line = entry/exit

---

## 🎯 Strategia Swing Trading Consigliata

```python
# 1. Verifica forza del trend
if ADX > 25 and ER > 0.5:
    # 2. Conferma direzione
    if SuperTrend == "UP" and Ichimoku_Cloud == "BULLISH" and LinReg_Slope > 0:
        # 3. Timing entry con momentum
        if RSI < 70 and TSI > TSI_Signal and MACD > MACD_Signal:
            # ✅ STRONG BUY SIGNAL
            entry_price = current_price
            stop_loss = entry_price - (1.5 * ATR)
            target = entry_price + (3 * ATR)  # Risk/Reward 1:2
```

### Quando Uscire (Exit Strategy)

- **Profit Target**: +3-5% raggiunto
- **Stop Loss**: Sceso sotto 1.5x ATR
- **Indicatori Inversi**: SuperTrend flip, TSI cross below signal
- **ADX Decline**: ADX scende sotto 20 (trend finito)

---

## 📈 Strategia Long-Term Investing Consigliata

```python
# 1. Analisi fundamentals
if Balance_Sheet == "STRONG" and Cash_Flow > 0:
    # 2. Trend di lungo periodo
    if Price > SMA_200 and MACD_Monthly == "BULLISH":
        # 3. Valutazione relativa
        if RSI_Monthly < 40:  # Zona accumulo
            # ✅ BUY AND HOLD
            # Holding: 6+ mesi
            # Rebalance: Quarterly
            position_size = portfolio * risk_allocation
```

### Quando Rivalutare (Rebalancing)

- **Quarterly Review**: Ogni 3 mesi
- **Fundamentals Change**: Se bilanci peggiorano
- **Secular Trend Reversal**: Prezzo sotto 200 SMA per 3 mesi
- **Target Reached**: +20-30% profit, consider taking partial profits

---

## 📁 File Structure

```
tradingagents/
├── default_config.py           # DEFAULT_CONFIG, SWING_CONFIG, INVESTING_CONFIG
├── dataflows/
│   ├── technical_calculations.py  # Nuovi indicatori
│   └── y_finance.py              # Aggiornato con nuovi indicatori
├── agents/
│   └── analysts/
│       └── market_analyst.py     # Prompt differenziati per swing/investing
└── graph/
    └── trading_graph.py         # Gestisce strategy_type

# File di esempio
swing_trading_example.py         # Esempi swing completi
investing_example.py             # Esempi investing completi
```

---

## 🔍 Come Funziona Internamente

### Strategy Type Detection

Il framework rileva automaticamente la strategia tramite `config["strategy_type"]`:

```python
# In market_analyst.py
config = get_config()
strategy_type = config.get("strategy_type", "swing")

if strategy_type == "swing":
    # Usa prompt con tutti i 17 indicatori tecnici
    # Focus su ADX, SuperTrend, TSI, Ichimoku
elif strategy_type == "investing":
    # Usa prompt con indicatori long-term
    # Focus su 200 SMA, fundamentals, MACD monthly
```

### Indicator Calculation

```python
# In y_finance.py _get_stock_stats_bulk()
ADVANCED_INDICATORS = [
    'adx', 'plus_di', 'minus_di', 'er',
    'supertrend', 'supertrend_direction',
    'linear_regression', 'linear_regression_slope', 'linear_regression_r2',
    'ichimoku_tenkan_sen', 'ichimoku_kijun_sen', ...
]

if indicator in ADVANCED_INDICATORS:
    # Usa technical_calculations.py
    from .technical_calculations import get_all_indicators
    indicators_dict = get_all_indicators(data, swing_mode=True)
else:
    # Usa stockstats legacy
    from stockstats import wrap
    df[indicator]
```

---

## 🧪 Testing

### Test Swing Trading

```bash
cd /workspaces/TradingAgents
python swing_trading_example.py
```

Output atteso:
```
🎯 SWING TRADING MODE - Analisi Breve Termine
  - Debate Rounds: 3
  - Analysts: market, social, news, fundamentals
  - Indicators: ADX, SuperTrend, TSI, Ichimoku, ...

📊 Analizzando NVDA...
✅ Decisione: BUY - Strong uptrend confirmed
   ADX: 32.5 (strong trend)
   SuperTrend: BULLISH
   TSI: 15.3 (positive momentum)
   ...
```

### Test Investing

```bash
python investing_example.py
```

Output atteso:
```
📈 INVESTING MODE - Analisi Lungo Termine
  - Debate Rounds: 5
  - LLM: gpt-5.2 (deep reasoning)
  - Focus: Fundamentals + Long-term trends

📊 Portfolio Analysis:
  SPY: HOLD - Steady growth
  AAPL: BUY - Strong fundamentals
  ...
```

---

## 🛠️ Personalizzazione Avanzata

### Custom Swing Config

```python
from tradingagents.default_config import SWING_CONFIG

custom_config = SWING_CONFIG.copy()
custom_config["max_debate_rounds"] = 5  # Più analisi
custom_config["deep_think_llm"] = "gpt-5.2"  # Model più potente
custom_config["data_vendors"]["news_data"] = "alpha_vantage"  # News premium

ta = TradingAgentsGraph(config=custom_config)
```

### Custom Indicators Selection

```python
# Solo tecnico puro (no sentiment, no fundamentals)
ta_technical_only = TradingAgentsGraph(
    selected_analysts=["market"],  # Solo market analyst
    config=SWING_CONFIG
)

# L'analyst richiederà automaticamente:
# - ADX, SuperTrend, TSI per swing
# - 200 SMA, fundamentals per investing
```

---

## 💡 Best Practices

### Per Swing Trading

✅ **DO:**
- Controlla ADX prima di ogni trade (> 25)
- Usa stop-loss a 1.5-2x ATR
- Cerca allineamento di 3+ indicatori
- Monitora giornalmente

❌ **DON'T:**
- Swing trade in mercati laterali (ADX < 20)
- Ignorare ER (noise ratio)
- Hold oltre 10 giorni se target non raggiunto
- Trade senza stop-loss

### Per Investing

✅ **DO:**
- Analisi fundamentals approfondita
- Check 200 SMA per trend secolare
- Diversifica portfolio (5+ assets)
- Rebalance quarterly

❌ **DON'T:**
- Panic sell su correzioni <10%
- Chase performance (buy high)
- Ignore fundamentals deterioration
- Over-concentrate (max 20% per asset)

---

## 📚 Risorse Aggiuntive

- [Technical Calculations Documentation](tradingagents/dataflows/technical_calculations.py)
- [Market Analyst Prompts](tradingagents/agents/analysts/market_analyst.py)
- [Default Configs](tradingagents/default_config.py)

---

## 🐛 Troubleshooting

### Errore: "Indicator not supported"

```python
# Assicurati che l'indicatore sia nella lista ADVANCED_INDICATORS
# o nei legacy indicators di stockstats
```

### Performance lenta con molti indicatori

```python
# Usa caching per dati storici
config["data_cache_dir"] = "/path/to/cache"

# Riduci look_back_days
look_back_days = 30  # Invece di 90
```

### Analisi investing troppo veloce

```python
# Aumenta debate rounds per analisi più profonda
INVESTING_CONFIG["max_debate_rounds"] = 8
INVESTING_CONFIG["max_risk_discuss_rounds"] = 5
```

---

## 📞 Support

Per domande o issue:
- GitHub Issues: [TradingAgents Issues](https://github.com/TauricResearch/TradingAgents/issues)
- Documentazione: Questo file + codice sorgente commentato

---

**Versione:** 2.0 - Dual Strategy Mode (Swing + Investing)  
**Data:** Febbraio 2026  
**Autore:** TauricResearch + AI Assistant
