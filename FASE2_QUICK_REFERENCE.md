# FASE 2 Quick Reference Guide

## 🚀 Five-Minute Start

```python
# 1. Initialize
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.scoring_engine import ScoringEngine

mtf = MultiTimeframeLayer()
scorer = ScoringEngine()

# 2. Fetch and score
data = mtf.fetch_symbol_mtf("AAPL")
long_score, short_score = scorer.score_mtf_signal(data)

# 3. Use results
print(f"LONG: {long_score.total_score:.0f}/100")
print(f"SHORT: {short_score.total_score:.0f}/100")
```

---

## 📂 Four Core Modules

| Module | Purpose | Key Class | Main Method |
|--------|---------|-----------|-------------|
| `cache_manager.py` | Smart CSV caching | `CacheManager` | `get_cached_or_fetch()` |
| `multi_timeframe.py` | Weekly + Daily sync | `MultiTimeframeLayer` | `fetch_symbol_mtf()` |
| `structure_detector.py` | Pivots + ChoCH/BOS | `SwingClassifier` | `classify_structure()` |
| `scoring_engine.py` | 0-100 signal score | `ScoringEngine` | `score_mtf_signal()` |

---

## 💾 Cache Manager

**Problem Solved**: 25 API calls/day limit

```python
cache = CacheManager()

# Auto-use cache if <1 day old, else fetch today's bar only
df = cache.get_cached_or_fetch(
    "SPY",
    fetch_fn=lambda: yf.download("SPY", ...),
    timeframe="daily"
)
```

**Result**: 12 symbols = 12 calls (not 24)

---

## 📊 Multi-Timeframe Data

**Structure**:
```python
mtf = MultiTimeframeLayer().fetch_symbol_mtf("SPY")

mtf.daily           # TimeframeData object
  ├─ ohlcv         # DataFrame with OHLCV
  ├─ indicators    # Dict of all 44 indicators
  └─ latest(name)  # Get latest value

mtf.weekly          # Same structure for weekly data
```

**Confluence Check**:
```python
is_valid, reason = mtf_layer.confluence_check_long(mtf)
# Checks: Weekly 200 SMA, SuperTrend, Daily ADX, Volume, Breakout
```

---

## 🎯 Structure Detection

```python
classifier = SwingClassifier()

# Get structure
structure = classifier.classify_structure(df)
# Returns: formation ('HH/LH', 'LL/LH', etc.)
#          direction (1=bull, -1=bear, 0=choppy)

# Detect reversals
has_choch, msg = classifier.detect_choch(df)
# "ChoCH UP: Broke swing high at 425.30"

# Get key levels
levels = classifier.get_key_levels(df)
# {'resistances': [r1, r2, r3], 'supports': [s1, s2, s3]}
```

---

## 🎯 Signal Scoring (0-100)

**Weighting**:
- 30% Trend Strength (ADX)
- 25% Confluence (Weekly + Daily)
- 20% Volume (VR)
- 15% Structure (ChoCH/BOS)
- 10% Risk (ATR%, Mean Reversion)

**Score Guide**:
- **75-100**: Strong - Trade it
- **50-75**: Moderate - Wait for confirmation
- **25-50**: Weak - Skip or limited size
- **0-25**: Invalid - Avoid

**Usage**:
```python
long_score, short_score = scorer.score_mtf_signal(mtf)

print(long_score.total_score)        # 78/100
print(long_score.adx_value)          # 38
print(long_score.volume_ratio)       # 1.75
print(long_score.strengths)          # ["Very strong trend...", ...]
```

---

## 💡 Common Patterns

### Pattern A: Screener (Scan Multiple Symbols)
```python
mtf_layer = MultiTimeframeLayer()
scorer = ScoringEngine()

all_scores = []
for symbol in ["SPY", "QQQ", "AAPL"]:
    mtf = mtf_layer.fetch_symbol_mtf(symbol)
    long, short = scorer.score_mtf_signal(mtf)
    all_scores.extend([long, short])

# Rank
top = scorer.rank_signals(all_scores)
```

### Pattern B: Single Symbol (Trading Decision)
```python
mtf = mtf_layer.fetch_symbol_mtf("AAPL")
long_score, short_score = scorer.score_mtf_signal(mtf)

if long_score.total_score > 75:
    print("✓ LONG setup valid")
    # Get levels, position size, etc.
```

### Pattern C: Agent Integration
```python
mtf = mtf_layer.fetch_symbol_mtf("SPY")
long_score, short_score = scorer.score_mtf_signal(mtf)

agent_state = {
    'signal_score': long_score.total_score,
    'adx': mtf.daily.latest('adx'),
    'volume_ratio': mtf.daily.latest('volume_ratio'),
    'weekly_trend': mtf.weekly.latest('supertrend_direction'),
}

# Pass to agent for smarter decision-making
```

---

## 🧪 Testing

```bash
# Run full test suite
python test_fase2_infrastructure.py

# Expected: 6/6 tests pass
# ✅ Cache Manager: PASSED
# ✅ Pivot Finder: PASSED
# ✅ Swing Classifier: PASSED
# ✅ Multi-Timeframe Layer: PASSED
# ✅ Scoring Engine: PASSED
# ✅ Full Integration: PASSED
```

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| "ModuleNotFoundError" | `pip install pandas numpy scipy yfinance` |
| Empty cache | First fetch takes longer (populates cache) |
| API timeout | Check internet, yfinance may be slow |
| Low scores | Market may be choppy (ADX < 25) |
| Conflicting signals | Wait for confluence (75+) before trading |

---

## 📈 Performance Tips

1. **Batch Processing**: Cache scores for multiple symbols
   ```python
   # Good
   mtf = mtf_layer.fetch_symbol_mtf("AAPL")
   long, short = scorer.score_mtf_signal(mtf)
   ```

2. **Reuse Data**: Don't fetch same symbol twice
   ```python
   # Good
   mtf = fetch_once()
   score = scorer.score_mtf_signal(mtf)
   structure = classifier.classify_structure(mtf.daily.ohlcv)
   ```

3. **Filter Early**: Pre-screen before detailed analysis
   ```python
   # Quick screening
   if signal.total_score < 50:
       continue  # Skip weak setups
   
   # Detailed analysis only for high-score setups
   ```

---

## 🔗 Integration Points

### 1. In Market Analyst Agent
```python
# File: tradingagents/agents/analysts/market_analyst.py
mtf = MultiTimeframeLayer().fetch_symbol_mtf(symbol)
long_score, short_score = ScoringEngine().score_mtf_signal(mtf)

# Use signal_score to validate/adjust analyst output
if long_score.total_score < 50:
    response = "Market not aligned for LONG"
```

### 2. In Research Manager
```python
# File: tradingagents/agents/managers/research_manager.py
mtf = MultiTimeframeLayer().fetch_symbol_mtf(symbol)

# Pass MTF data to debaters for validation
debater_state = {
    ...existing state...,
    'mtf_signal_score': long_score.total_score,
    'weekly_trend': mtf.weekly.latest('supertrend_direction'),
}
```

### 3. In Trader Agent
```python
# File: tradingagents/agents/trader/trader.py
mtf = MultiTimeframeLayer().fetch_symbol_mtf(symbol)
long_score, short_score = ScoringEngine().score_mtf_signal(mtf)

# Use for position sizing based on confidence
if long_score.total_score >= 75:
    position_size = "full"  # Allocate max position
elif long_score.total_score >= 50:
    position_size = "half"  # Reduce size
else:
    position_size = "micro"  # Minimal size
```

---

## 📚 Files to Read

1. **FASE2_ARCHITECTURE.md** - Complete technical spec
2. **fase2_integration_examples.py** - Working code examples
3. **test_fase2_infrastructure.py** - Validation tests
4. Individual module docstrings for detailed API

---

## ⚡ Key Takeaways

✅ **Cache Manager**: Solves 25 API calls/day constraint
✅ **Multi-Timeframe**: Weekly filter + Daily execution = higher win rate
✅ **Structure Detection**: ChoCH/BOS validation = fewer false signals
✅ **Signal Scoring**: Single 0-100 number for easy decision-making
✅ **Integration Ready**: Drop into agents, screeners, or traders

---

## 🎓 Learning Path

1. **Beginner**: Run `test_fase2_infrastructure.py` to see it work
2. **Intermediate**: Try Pattern A (Screener) in `fase2_integration_examples.py`
3. **Advanced**: Integrate into your agent with Pattern C
4. **Expert**: Customize scoring weights, add new indicators to engine

---

**Status**: ✅ READY FOR PRODUCTION

Last Updated: 2025-02-25
