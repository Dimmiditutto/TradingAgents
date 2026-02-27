# MTF Swing System — Guida all'uso

Sistema di swing trading su azioni USA (S&P 500 / Nasdaq) con analisi
multi-timeframe (Daily + Weekly), struttura di mercato e dashboard HTML interattiva.

---

## Setup rapido

```bash
# 1. Installa le dipendenze
pip install pandas numpy scipy

# 2. Configura la watchlist e la API key
cp config.template.json config.json
# → apri config.json e inserisci la tua API key Alpha Vantage
#   (gratuita su https://www.alphavantage.co/support/#api-key)
#   e modifica la watchlist con i tuoi ticker

# 3. Test immediato con dati sintetici (senza API key)
python screener.py scan --synthetic
python screener.py backtest --synthetic --tickers 5
```

---

## Comandi

| Comando | Descrizione |
|---|---|
| `python screener.py scan` | Screening live — genera segnali e apre la dashboard |
| `python screener.py scan --synthetic` | Stessa cosa con dati generati (test/demo) |
| `python screener.py backtest --tickers 10` | Backtest su 10 ticker dalla watchlist |
| `python screener.py backtest --synthetic` | Backtest demo senza API |
| `python screener.py dashboard` | Riapre l'ultima dashboard generata |

**Opzioni:**
- `--score 70`  — soglia minima dello score (default 60)
- `--tickers N` — quanti ticker per il backtest (default 10)

---

## Struttura file

```
swing_system/
├── indicators.py        — tutti gli indicatori tecnici (51 colonne)
├── market_structure.py  — pivot, HH/LH/HL/LL, CHoCH, BOS, MTF
├── scoring.py           — punteggio 0-100 con 5 sub-score + filtri + stop/target
├── backtest.py          — walk-forward no-lookahead, 12 metriche
├── dashboard.py         — generatore HTML (scan + backtest + posizioni)
├── data_layer.py        — Alpha Vantage client, cache CSV, dati sintetici
├── screener.py          — runner principale (CLI)
├── config.template.json — template configurazione
└── output/              — dashboard HTML e CSV generati
```

---

## Indicatori implementati

**Moving Averages:** EMA10, SMA50, SMA200, VWMA20, pct_from_200sma

**Momentum:** RSI(14), TSI(13/7), TSI Signal, MACD(12/26/9), MACD Hist, MACD Hist Slope

**Volatility:** Bollinger Bands(20), Bandwidth, %B, ATR(14), ATR%

**Trend Strength:** ADX(14), +DI, -DI, Efficiency Ratio(14)

**Trend Direction:** SuperTrend(10, 3.0), Linear Regression(20), LR Slope, LR R²

**Ichimoku:** Tenkan(9), Kijun(26), Senkou A/B, Chikou, Cloud Bias, TK Cross

**Volume:** VWMA, Volume SMA20, Volume Ratio, MFI(14)

**Structure:** Donchian Channel(20), breakout signals

---

## Logica del punteggio (0–100)

| Blocco | Peso | Misura |
|---|---|---|
| Struttura MTF | 30% | CHoCH/BOS + confluenza weekly/daily |
| Trend Strength | 25% | ADX + ER + SuperTrend + LR R² |
| Momentum | 25% | RSI + TSI + MACD slope + MFI |
| Volatility Setup | 10% | Boll Bandwidth + %B |
| Volume | 10% | Volume Ratio |

**Filtri obbligatori (bloccano il segnale):**
- Weekly trend = UPTREND (per long)
- Close > SMA200
- ADX ≥ 20
- SuperTrend bullish
- ATR% tra 0.5% e 6%
- Non oltre +25% dalla SMA200

---

## Struttura di mercato — logica CHoCH vs BOS

```
UPTREND   (HH → HL → HH → HL):
  BOS_UP    = nuovo HH confermato         → continuazione bullish
  CHoCH_DOWN = rottura sotto ultimo HL    → inversione bearish ⚠

DOWNTREND (LH → LL → LH → LL):
  BOS_DOWN  = nuovo LL confermato         → continuazione bearish
  CHoCH_UP  = rottura sopra ultimo LH     → inversione bullish ⚠

I CHoCH sono i segnali di maggiore qualità:
  indicano un cambio di struttura, non solo la conferma del trend esistente.
```

---

## Stop e target (ATR-based)

```
LONG:
  Entry  = close del giorno del segnale
  Stop   = entry - 1.5 × ATR   (configurabile)
  T1     = entry + 2.0 × ATR   → R/R = 1.33
  T2     = entry + 3.5 × ATR   (o prossimo pivot high)

SHORT:
  Stop   = entry + 1.5 × ATR
  T1     = entry - 2.0 × ATR
  T2     = entry - 3.5 × ATR   (o prossimo pivot low)
```

---

## Metriche backtest

- Win Rate, Profit Factor, Avg R/R
- Total PnL %, CAGR
- Sharpe Ratio, Sortino Ratio
- Max Drawdown, Avg Drawdown
- Total Trades, Durata media
- Equity Curve (base 100, rischio 1%/trade)

Breakdown per: evento strutturale, direzione, score bucket, durata, exit reason.

---

## Alpha Vantage — gestione limite API

La versione gratuita di Alpha Vantage permette **25 richieste al giorno**.

Il sistema usa una **cache locale** in `data/cache/<TICKER>.csv`:
- Prima esecuzione: scarica la history completa (1 call per ticker)
- Esecuzioni successive: scarica solo l'ultima barra se la cache è aggiornata (0-1 call)

Con 15 ticker in watchlist:
- Primo giorno: 15 API calls
- Giorni successivi: 0-5 API calls (solo ticker con cache scaduta)

---

## Consigli operativi per swing 2-5 giorni

1. **Esegui lo scan ogni mattina prima dell'apertura** (pre-market US = 14:00-15:30 IT)
2. **Priorità ai CHoCH** rispetto ai BOS: segnalano cambiamento di struttura
3. **Volume Ratio > 1.5** alla rottura è un ottimo filtro aggiuntivo
4. **Non tradare contro il weekly trend**: il filtro è attivo di default
5. **ADX < 20** = mercato in range, segnali meno affidabili (filtrato automaticamente)
6. **Backtest suggerito**: 1 anno di dati, step=5, poi confronta WR per evento strutturale
   — in genere CHoCH_UP in uptrend weekly ha il WR più alto

---

## Personalizzazione watchlist

Modifica `config.json`:

```json
{
  "api_key": "LA_TUA_KEY",
  "watchlist": ["AAPL", "NVDA", "MSFT"],
  "min_score": 68,
  "filters": {
    "require_adx_min": 22,
    "max_atr_pct": 5.0
  }
}
```

I parametri in `filters` sovrascrivono i default — puoi modificare solo quelli
che ti interessano, gli altri rimangono ai valori standard.
