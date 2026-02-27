"""
scoring.py
──────────
Converte indicatori tecnici + struttura di mercato in un punteggio swing 0-100.

ARCHITETTURA DEL PUNTEGGIO:
  Il punteggio è diviso in 5 blocchi tematici con pesi configurabili.
  Ogni blocco calcola un sub-score 0-100 in modo indipendente.
  Il punteggio finale è la media pesata dei sub-score.

  Blocco             Peso default   Cosa misura
  ─────────────────────────────────────────────────────────────────────
  Struttura (MTF)      30%          CHoCH/BOS + confluenza weekly/daily
  Trend Strength       25%          ADX + ER + SuperTrend + LR R²
  Momentum             25%          RSI + TSI + MACD + MFI
  Volatility Setup     10%          Boll bandwidth + posizione nelle bande
  Volume Confirmation  10%          Volume ratio + MFI conferma

SEGNALI DI ENTRATA (LONG):
  Tutti i filtri obbligatori devono essere true:
    - weekly trend UPTREND (macro filtro)
    - close > SMA200 (non in territorio di mean-reversion estrema)
    - ADX > 20 (mercato in trend, non ranging)
    - SuperTrend direction = +1 (trend bullish)
  Poi score >= soglia configurabile (default: 65)

STOP E TARGET (ATR-based):
  Stop loss:  close - N * ATR  (default N=1.5)
  Target 1:   close + M * ATR  (default M=2.0)  → R/R = 1.33
  Target 2:   prossimo livello strutturale (pivot high precedente)
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE PESI E SOGLIE
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "structure":   0.30,
    "trend":       0.25,
    "momentum":    0.25,
    "volatility":  0.10,
    "volume":      0.10,
}

DEFAULT_FILTERS = {
    "require_weekly_uptrend":   True,
    "require_above_200sma":     True,
    "require_adx_min":          20.0,
    "require_supertrend_bull":  True,
    "max_pct_from_200sma":      25.0,   # esclude titoli >25% sopra la 200
    "min_atr_pct":              0.5,    # esclude titoli con volatilità troppo bassa
    "max_atr_pct":              8.0,    # esclude titoli con volatilità eccessiva
}

DEFAULT_TRADE = {
    "stop_atr_mult":   1.5,
    "target1_atr_mult": 2.0,
    "target2_atr_mult": 3.5,
}


# ──────────────────────────────────────────────────────────────────────────────
# DATACLASS RISULTATO
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SwingSignal:
    ticker:          str
    timestamp:       pd.Timestamp
    direction:       str            # "LONG" o "SHORT"
    score:           float          # 0-100
    sub_scores:      dict = field(default_factory=dict)
    filters_passed:  bool = True
    filter_failures: list = field(default_factory=list)

    # Prezzi operativi
    entry_price:     float = 0.0
    stop_loss:       float = 0.0
    target1:         float = 0.0
    target2:         float = 0.0
    atr:             float = 0.0
    atr_pct:         float = 0.0
    risk_reward:     float = 0.0    # target1 R/R

    # Contesto
    weekly_trend:    str = "UNDEFINED"
    daily_trend:     str = "UNDEFINED"
    structure_event: str = ""
    adx:             float = 0.0
    rsi:             float = 0.0
    volume_ratio:    float = 0.0

    def to_dict(self) -> dict:
        return {
            "ticker":          self.ticker,
            "timestamp":       str(self.timestamp),
            "direction":       self.direction,
            "score":           round(self.score, 1),
            "filters_passed":  self.filters_passed,
            "filter_failures": self.filter_failures,
            "entry_price":     round(self.entry_price, 4),
            "stop_loss":       round(self.stop_loss, 4),
            "target1":         round(self.target1, 4),
            "target2":         round(self.target2, 4),
            "risk_reward":     round(self.risk_reward, 2),
            "atr_pct":         round(self.atr_pct, 2),
            "weekly_trend":    self.weekly_trend,
            "daily_trend":     self.daily_trend,
            "structure_event": self.structure_event,
            "adx":             round(self.adx, 1),
            "rsi":             round(self.rsi, 1),
            "volume_ratio":    round(self.volume_ratio, 2),
            **{f"score_{k}": round(v, 1) for k, v in self.sub_scores.items()},
        }


# ──────────────────────────────────────────────────────────────────────────────
# HELPER — NORMALIZZAZIONE
# ──────────────────────────────────────────────────────────────────────────────

def _scale(value: float, lo: float, hi: float) -> float:
    """Scala un valore nel range [lo, hi] a [0, 1]."""
    if hi <= lo:
        return 0.5
    return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))


def _score_rsi_long(rsi: float) -> float:
    """
    RSI ideale per entrata LONG in swing 2-5gg:
    - Zona 40-60: score pieno (né overbought né oversold estremo)
    - Zona 30-40: score buono (pullback con possibile recupero)
    - < 30: score ridotto (oversold estremo, possibile capitolazione)
    - > 70: score basso (overbought, rischio di pullback imminente)
    """
    if rsi < 30:    return 0.3
    if rsi < 40:    return 0.7
    if rsi <= 60:   return 1.0
    if rsi <= 70:   return 0.6
    return 0.2


def _score_rsi_short(rsi: float) -> float:
    if rsi > 70:    return 0.3
    if rsi > 60:    return 0.7
    if rsi >= 40:   return 1.0
    if rsi >= 30:   return 0.6
    return 0.2


# ──────────────────────────────────────────────────────────────────────────────
# SUB-SCORE: STRUTTURA (30%)
# ──────────────────────────────────────────────────────────────────────────────

def score_structure(row: pd.Series, mtf: dict, direction: str) -> float:
    """
    Sub-score struttura: 0-100
    Componenti:
      - Confluenza MTF (weekly + daily allineati):   40 punti
      - Tipo di segnale strutturale (CHoCH > BOS):   30 punti
      - Struttura intatta (no LL in uptrend):        20 punti
      - Volume alla rottura strutturale:             10 punti
    """
    score = 0.0

    is_long = direction == "LONG"

    # ── MTF confluence (40 pt)
    if is_long and mtf.get("long_confluence", False):
        score += 40
    elif not is_long and mtf.get("short_confluence", False):
        score += 40
    else:
        # Parziale: solo daily allineato
        daily_trend = mtf.get("daily_trend", "UNDEFINED")
        if is_long and daily_trend == "UPTREND":
            score += 20
        elif not is_long and daily_trend == "DOWNTREND":
            score += 20

    # ── Tipo segnale strutturale (30 pt)
    last_sig = mtf.get("daily_structure", {}).get("last_signal", {})
    if last_sig:
        event = last_sig.get("event", "")
        if is_long and event == "CHoCH_UP":
            score += 30    # CHoCH = segnale di inversione → massima priorità
        elif is_long and event == "BOS_UP":
            score += 20    # BOS = conferma trend → buono ma non eccezionale
        elif not is_long and event == "CHoCH_DOWN":
            score += 30
        elif not is_long and event == "BOS_DOWN":
            score += 20

    # ── Struttura intatta (20 pt)
    daily_struct = mtf.get("daily_structure", {})
    if daily_struct.get("structure_intact", False):
        score += 20

    # ── Volume alla rottura (10 pt)
    vol_ratio = last_sig.get("volume_ratio", 1.0) if last_sig else 1.0
    if vol_ratio >= 1.5:
        score += 10
    elif vol_ratio >= 1.0:
        score += 5

    return min(score, 100.0)


# ──────────────────────────────────────────────────────────────────────────────
# SUB-SCORE: TREND STRENGTH (25%)
# ──────────────────────────────────────────────────────────────────────────────

def score_trend_strength(row: pd.Series, direction: str) -> float:
    """
    Sub-score forza del trend: 0-100
    Componenti:
      - ADX (>25=forte, 20-25=medio, <20=debole):   35 punti
      - Efficiency Ratio (>0.5=efficiente):          25 punti
      - SuperTrend allineato:                        25 punti
      - Linear Regression R² (>0.6=lineare):        15 punti
    """
    score    = 0.0
    is_long  = direction == "LONG"

    # ── ADX (35 pt)
    adx = row.get("adx", 0)
    adx_score = _scale(adx, 15, 45)
    score += adx_score * 35

    # ── ER (25 pt)
    er = row.get("er", 0)
    score += _scale(er, 0.3, 0.8) * 25

    # ── SuperTrend (25 pt)
    st_dir = row.get("supertrend_direction", 0)
    if is_long and st_dir == -1:      # -1 = bullish in Pine convention
        score += 25
    elif not is_long and st_dir == 1: # 1 = bearish
        score += 25
    # Nota: la convenzione SuperTrend del modulo indicators usa +1=bearish, -1=bullish
    # coerente con ta.supertrend Pine v6

    # ── LR R² (15 pt)
    r2 = row.get("linear_regression_r2", 0)
    score += _scale(r2, 0.3, 0.9) * 15

    return min(score, 100.0)


# ──────────────────────────────────────────────────────────────────────────────
# SUB-SCORE: MOMENTUM (25%)
# ──────────────────────────────────────────────────────────────────────────────

def score_momentum(row: pd.Series, direction: str) -> float:
    """
    Sub-score momentum: 0-100
    Componenti:
      - RSI posizione ideale:         30 punti
      - TSI > TSI signal (crossover): 25 punti
      - MACD histogram slope:         25 punti
      - MFI conferma:                 20 punti
    """
    score   = 0.0
    is_long = direction == "LONG"

    # ── RSI (30 pt)
    rsi = row.get("rsi", 50)
    rsi_s = _score_rsi_long(rsi) if is_long else _score_rsi_short(rsi)
    score += rsi_s * 30

    # ── TSI crossover (25 pt): TSI > signal = momentum long
    tsi    = row.get("tsi", 0)
    tsi_s  = row.get("tsi_signal", 0)
    if is_long and tsi > tsi_s:
        # Più il gap è ampio, più il segnale è forte
        score += min(_scale(tsi - tsi_s, 0, 5) * 25, 25)
    elif not is_long and tsi < tsi_s:
        score += min(_scale(tsi_s - tsi, 0, 5) * 25, 25)

    # ── MACD histogram slope (25 pt): slope positiva = accelerazione bullish
    macdh_slope = row.get("macdh_slope", 0)
    if is_long and macdh_slope > 0:
        score += min(_scale(macdh_slope, 0, 0.5) * 25, 25)
    elif not is_long and macdh_slope < 0:
        score += min(_scale(-macdh_slope, 0, 0.5) * 25, 25)

    # ── MFI (20 pt): > 50 bullish, zona 40-60 ideale per entrata
    mfi = row.get("mfi", 50)
    if is_long:
        mfi_s = _scale(mfi, 30, 70)
    else:
        mfi_s = _scale(70 - mfi, 0, 40)
    score += mfi_s * 20

    return min(score, 100.0)


# ──────────────────────────────────────────────────────────────────────────────
# SUB-SCORE: VOLATILITY SETUP (10%)
# ──────────────────────────────────────────────────────────────────────────────

def score_volatility_setup(row: pd.Series, direction: str) -> float:
    """
    Sub-score setup di volatilità: 0-100
    Per swing 2-5 giorni si preferisce:
      - Bandwidth bassa (compressione prima del breakout): 50 pt
      - %B in zona di entrata ideale:                     50 pt

    %B ideale LONG:  0.2-0.5 (prezzo nella metà inferiore delle bande)
    %B ideale SHORT: 0.5-0.8 (prezzo nella metà superiore)
    """
    score   = 0.0
    is_long = direction == "LONG"

    # ── Bollinger Bandwidth (50 pt): bassa = coiling = setup pre-breakout
    bw = row.get("boll_bandwidth", 10)
    # Bandwidth < 5% su azioni USA = compressione significativa
    bw_score = _scale(15 - bw, 0, 10)   # inversione: bassa bw → score alto
    score += bw_score * 50

    # ── %B posizione (50 pt)
    pct_b = row.get("boll_pct_b", 0.5)
    if is_long:
        # Zona ideale: 0.2-0.6 (pullback verso il centro o bande inferiori)
        if 0.2 <= pct_b <= 0.6:
            score += 50
        elif pct_b < 0.2:
            score += 30   # oversold, possibile rimbalzo
        else:
            score += 10   # già in zona alta, meno setup ideale
    else:
        if 0.4 <= pct_b <= 0.8:
            score += 50
        elif pct_b > 0.8:
            score += 30
        else:
            score += 10

    return min(score, 100.0)


# ──────────────────────────────────────────────────────────────────────────────
# SUB-SCORE: VOLUME CONFIRMATION (10%)
# ──────────────────────────────────────────────────────────────────────────────

def score_volume(row: pd.Series) -> float:
    """
    Sub-score conferma volume: 0-100
    Volume > media = partecipazione reale al movimento.
    Senza volume, il breakout è sospetto.
    """
    vol_ratio = row.get("volume_ratio", 1.0)
    # 1.5x = 50pt, 2x = 100pt (linearmente)
    return float(np.clip(_scale(vol_ratio, 0.8, 2.0) * 100, 0, 100))


# ──────────────────────────────────────────────────────────────────────────────
# FILTRI OBBLIGATORI
# ──────────────────────────────────────────────────────────────────────────────

def apply_filters(row: pd.Series,
                  mtf: dict,
                  direction: str,
                  filters: dict = None) -> tuple[bool, list]:
    """
    Verifica i filtri obbligatori. Restituisce (passed, [failures]).
    Un singolo filtro fallito blocca il segnale.
    """
    if filters is None:
        filters = DEFAULT_FILTERS

    failures = []
    is_long  = direction == "LONG"

    # ── Filtro macro trend weekly
    if filters.get("require_weekly_uptrend", True):
        weekly_trend = mtf.get("weekly_trend", "UNDEFINED")
        if is_long and weekly_trend != "UPTREND":
            failures.append(f"weekly_trend={weekly_trend} (richiesto UPTREND)")
        elif not is_long and weekly_trend != "DOWNTREND":
            failures.append(f"weekly_trend={weekly_trend} (richiesto DOWNTREND)")

    # ── Filtro SMA200
    if filters.get("require_above_200sma", True):
        close     = row.get("close", 0)
        sma200    = row.get("close_200_sma", 0)
        if is_long and close < sma200:
            failures.append(f"close({close:.2f}) < SMA200({sma200:.2f})")
        elif not is_long and close > sma200:
            failures.append(f"close({close:.2f}) > SMA200({sma200:.2f}) (short sopra SMA200)")

    # ── Filtro ADX minimo
    adx_min = filters.get("require_adx_min", 20)
    adx     = row.get("adx", 0)
    if adx < adx_min:
        failures.append(f"ADX={adx:.1f} < {adx_min} (mercato ranging)")

    # ── Filtro SuperTrend direction
    if filters.get("require_supertrend_bull", True):
        st_dir = row.get("supertrend_direction", 0)
        if is_long and st_dir != -1:
            failures.append(f"SuperTrend direction={st_dir} (richiesto -1 = bullish)")
        elif not is_long and st_dir != 1:
            failures.append(f"SuperTrend direction={st_dir} (richiesto +1 = bearish)")

    # ── Filtro pct_from_200sma (titoli in territorio estremo)
    max_pct = filters.get("max_pct_from_200sma", 25)
    pct_200 = row.get("pct_from_200sma", 0)
    if is_long and pct_200 > max_pct:
        failures.append(f"pct_from_200sma={pct_200:.1f}% > {max_pct}% (mean-reversion risk)")

    # ── Filtro ATR% (volatilità min/max)
    atr_pct = row.get("atr_pct", 0)
    if atr_pct < filters.get("min_atr_pct", 0.5):
        failures.append(f"ATR%={atr_pct:.2f}% < {filters['min_atr_pct']}% (bassa volatilità)")
    if atr_pct > filters.get("max_atr_pct", 8):
        failures.append(f"ATR%={atr_pct:.2f}% > {filters['max_atr_pct']}% (volatilità eccessiva)")

    return len(failures) == 0, failures


# ──────────────────────────────────────────────────────────────────────────────
# CALCOLO STOP E TARGET
# ──────────────────────────────────────────────────────────────────────────────

def compute_trade_levels(row: pd.Series,
                         direction: str,
                         mtf: dict,
                         trade_params: dict = None) -> dict:
    """
    Calcola entry, stop loss e target basati su ATR e struttura.
    """
    if trade_params is None:
        trade_params = DEFAULT_TRADE

    close    = row.get("close", 0)
    atr      = row.get("atr", 0)
    is_long  = direction == "LONG"
    mult_sl  = trade_params["stop_atr_mult"]
    mult_t1  = trade_params["target1_atr_mult"]
    mult_t2  = trade_params["target2_atr_mult"]

    if is_long:
        stop   = close - mult_sl * atr
        target1 = close + mult_t1 * atr
        target2 = close + mult_t2 * atr

        # Target 2 strutturale: prossimo pivot high (se disponibile)
        last_high = mtf.get("daily_structure", {}).get("last_high", {})
        if last_high and last_high.get("price", 0) > close:
            target2 = max(target2, last_high["price"])
    else:
        stop    = close + mult_sl * atr
        target1 = close - mult_t1 * atr
        target2 = close - mult_t2 * atr

        last_low = mtf.get("daily_structure", {}).get("last_low", {})
        if last_low and last_low.get("price", 0) < close:
            target2 = min(target2, last_low["price"])

    risk    = abs(close - stop)
    reward  = abs(target1 - close)
    rr      = reward / risk if risk > 0 else 0.0

    return {
        "entry":  close,
        "stop":   stop,
        "t1":     target1,
        "t2":     target2,
        "rr":     rr,
    }


# ──────────────────────────────────────────────────────────────────────────────
# SCORING PRINCIPALE
# ──────────────────────────────────────────────────────────────────────────────

def score_ticker(ticker: str,
                 df: pd.DataFrame,
                 mtf: dict,
                 direction: str = "LONG",
                 weights: dict = None,
                 filters: dict = None,
                 trade_params: dict = None,
                 min_score: float = 60.0) -> Optional[SwingSignal]:
    """
    Calcola il punteggio swing per un ticker.

    Args:
        ticker:     simbolo
        df:         DataFrame con tutti gli indicatori calcolati
        mtf:        dizionario struttura MTF da market_structure.analyze()
        direction:  "LONG" o "SHORT"
        min_score:  soglia minima per generare un segnale

    Returns:
        SwingSignal se score >= min_score e filtri passati, None altrimenti
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    if df.empty or len(df) < 50:
        return None

    row = df.iloc[-1]   # ultima barra disponibile (close confermata)
    ts  = df.index[-1]

    # ── Filtri obbligatori
    passed, failures = apply_filters(row, mtf, direction, filters)

    # ── Sub-scores
    sub = {
        "structure":  score_structure(row, mtf, direction),
        "trend":      score_trend_strength(row, direction),
        "momentum":   score_momentum(row, direction),
        "volatility": score_volatility_setup(row, direction),
        "volume":     score_volume(row),
    }

    # ── Punteggio pesato
    total = sum(sub[k] * weights.get(k, 0) for k in sub)

    if total < min_score or not passed:
        # Ritorna comunque il segnale se richiesto, ma con flags
        if total < min_score:
            return None   # sotto soglia: non includere nello screener

    # ── Livelli di trade
    levels = compute_trade_levels(row, direction, mtf, trade_params)

    # ── Contesto
    last_sig = mtf.get("daily_structure", {}).get("last_signal") or {}

    sig = SwingSignal(
        ticker          = ticker,
        timestamp       = ts,
        direction       = direction,
        score           = round(total, 1),
        sub_scores      = sub,
        filters_passed  = passed,
        filter_failures = failures,
        entry_price     = levels["entry"],
        stop_loss       = levels["stop"],
        target1         = levels["t1"],
        target2         = levels["t2"],
        atr             = row.get("atr", 0),
        atr_pct         = row.get("atr_pct", 0),
        risk_reward     = levels["rr"],
        weekly_trend    = mtf.get("weekly_trend", "UNDEFINED"),
        daily_trend     = mtf.get("daily_trend", "UNDEFINED"),
        structure_event = last_sig.get("event", ""),
        adx             = row.get("adx", 0),
        rsi             = row.get("rsi", 50),
        volume_ratio    = row.get("volume_ratio", 1.0),
    )

    return sig if passed else None


def score_both_directions(ticker: str,
                          df: pd.DataFrame,
                          mtf: dict,
                          **kwargs) -> list[SwingSignal]:
    """Valuta entrambe le direzioni e restituisce i segnali validi."""
    signals = []
    for direction in ("LONG", "SHORT"):
        sig = score_ticker(ticker, df, mtf, direction=direction, **kwargs)
        if sig is not None:
            signals.append(sig)
    return signals


# necessario per il type hint Optional
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from indicators import compute_all
    from market_structure import analyze

    np.random.seed(1)
    n      = 300
    dates  = pd.date_range("2023-01-02", periods=n, freq="B")
    close  = 150 + np.cumsum(np.random.randn(n) * 1.5 + 0.15)
    high   = close + np.abs(np.random.randn(n))
    low    = close - np.abs(np.random.randn(n))
    volume = np.random.randint(2_000_000, 20_000_000, n).astype(float)

    df_raw = pd.DataFrame({
        "open": close, "high": high, "low": low,
        "close": close, "volume": volume
    }, index=dates)

    df   = compute_all(df_raw)
    mtf  = analyze(df, include_weekly=True)["mtf"] if "mtf" in analyze(df) else {}

    # Patch: usa dizionario dummy se mtf mancante (dati sintetici brevi)
    if not mtf:
        mtf = {
            "weekly_trend": "UPTREND", "daily_trend": "UPTREND",
            "long_confluence": True, "short_confluence": False,
            "daily_structure": {
                "structure_intact": True,
                "last_signal": {"event": "BOS_UP", "volume_ratio": 1.8},
                "last_high": {"price": close[-1] * 1.02},
                "last_low":  {"price": close[-1] * 0.97},
            }
        }

    sig = score_ticker("TEST", df, mtf, direction="LONG", min_score=0)
    if sig:
        print(f"✓ score_ticker: score={sig.score}  R/R={sig.risk_reward:.2f}")
        print(f"  sub-scores: { {k: round(v,1) for k,v in sig.sub_scores.items()} }")
        print(f"  entry={sig.entry_price:.2f}  stop={sig.stop_loss:.2f}  T1={sig.target1:.2f}")
        print(f"  ADX={sig.adx:.1f}  RSI={sig.rsi:.1f}  Vol={sig.volume_ratio:.2f}x")
