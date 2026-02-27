"""
market_structure.py
────────────────────
Identifica la struttura di mercato su dati OHLCV:
  - Pivot high/low (massimi e minimi relativi)
  - Classificazione HH / LH / HL / LL
  - Break of Structure (BOS) — conferma del trend
  - Change of Character (CHoCH) — segnale di inversione
  - Struttura multi-timeframe (daily + weekly)
  - Export CSV/JSON dei segnali

LOGICA CHoCH vs BOS:
  In un uptrend (sequenza HH→HL):
    BOS_UP    = prezzo rompe sopra l'ultimo HH → continuazione
    CHoCH_DOWN = prezzo rompe sotto l'ultimo HL → inversione bearish

  In un downtrend (sequenza LH→LL):
    BOS_DOWN  = prezzo rompe sotto l'ultimo LL → continuazione
    CHoCH_UP  = prezzo rompe sopra l'ultimo LH → inversione bullish
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# TIPI
# ──────────────────────────────────────────────────────────────────────────────

class SwingLabel(str, Enum):
    HH = "HH"
    LH = "LH"
    HL = "HL"
    LL = "LL"

class StructureEvent(str, Enum):
    BOS_UP     = "BOS_UP"
    BOS_DOWN   = "BOS_DOWN"
    CHOCH_UP   = "CHoCH_UP"
    CHOCH_DOWN = "CHoCH_DOWN"

class TrendState(str, Enum):
    UPTREND   = "UPTREND"
    DOWNTREND = "DOWNTREND"
    UNDEFINED = "UNDEFINED"


@dataclass
class Pivot:
    bar_index:  int
    timestamp:  pd.Timestamp
    price:      float
    is_high:    bool            # True=pivot high, False=pivot low
    label:      Optional[SwingLabel] = None
    prominence: float = 0.0
    volume:     float = 0.0

    @property
    def label_str(self) -> str:
        return self.label.value if self.label else "?"

    def to_dict(self) -> dict:
        return {
            "bar_index":  self.bar_index,
            "timestamp":  str(self.timestamp),
            "price":      round(self.price, 6),
            "type":       "HIGH" if self.is_high else "LOW",
            "label":      self.label_str,
            "prominence": round(self.prominence, 6),
            "volume":     round(self.volume, 0),
        }


@dataclass
class StructureSignal:
    bar_index:  int
    timestamp:  pd.Timestamp
    event:      StructureEvent
    price:      float           # prezzo di chiusura al momento del segnale
    level:      float           # livello strutturale rotto
    prev_pivot: Pivot           # pivot che definiva il livello
    trend_before: TrendState
    volume_ratio: float = 1.0   # volume/sma20 al momento della rottura

    @property
    def is_bullish(self) -> bool:
        return self.event in (StructureEvent.BOS_UP, StructureEvent.CHOCH_UP)

    @property
    def is_choch(self) -> bool:
        return self.event in (StructureEvent.CHOCH_UP, StructureEvent.CHOCH_DOWN)

    def to_dict(self) -> dict:
        return {
            "bar_index":    self.bar_index,
            "timestamp":    str(self.timestamp),
            "event":        self.event.value,
            "price":        round(self.price, 6),
            "level":        round(self.level, 6),
            "trend_before": self.trend_before.value,
            "volume_ratio": round(self.volume_ratio, 2),
            "is_bullish":   self.is_bullish,
            "is_choch":     self.is_choch,
        }


# ──────────────────────────────────────────────────────────────────────────────
# IDENTIFICAZIONE PIVOT
# ──────────────────────────────────────────────────────────────────────────────

def find_pivots(df: pd.DataFrame,
                left_bars: int = 5,
                right_bars: int = 5,
                min_prominence_pct: float = 1.0) -> list[Pivot]:
    """
    Identifica pivot high e low usando un approccio rolling window.
    Un pivot high alla barra i richiede:
      - high[i] == max(high[i-left : i+right+1])
      - rilievo (prominence) >= min_prominence_pct% del prezzo

    Zero lookahead: il pivot viene confermato solo dopo right_bars barre.
    Il chiamante deve usare il bar_index originale, non quello spostato.

    Args:
        df:                  DataFrame OHLCV con DatetimeIndex
        left_bars:           barre a sinistra per identificazione
        right_bars:          barre a destra per conferma (ritardo)
        min_prominence_pct:  rilievo minimo come % del prezzo

    Returns:
        Lista di Pivot ordinati per bar_index
    """
    highs    = df["high"].values
    lows     = df["low"].values
    closes   = df["close"].values
    volumes  = df["volume"].values if "volume" in df.columns else np.ones(len(df))
    n        = len(df)
    pivots   = []

    for i in range(left_bars, n - right_bars):
        # ── Pivot HIGH
        window_h = highs[i - left_bars : i + right_bars + 1]
        if highs[i] == window_h.max():
            # Calcola prominence: differenza tra il picco e il massimo
            # dei minimi di entrambi i lati della finestra
            left_min  = lows[i - left_bars : i].min()  if i > left_bars else lows[i]
            right_min = lows[i + 1 : i + right_bars + 1].min() if i + right_bars < n else lows[i]
            prominence = highs[i] - max(left_min, right_min)
            prom_pct   = prominence / highs[i] * 100 if highs[i] > 0 else 0

            if prom_pct >= min_prominence_pct:
                pivots.append(Pivot(
                    bar_index  = i,
                    timestamp  = df.index[i],
                    price      = highs[i],
                    is_high    = True,
                    prominence = prominence,
                    volume     = volumes[i],
                ))

        # ── Pivot LOW
        window_l = lows[i - left_bars : i + right_bars + 1]
        if lows[i] == window_l.min():
            left_max  = highs[i - left_bars : i].max()  if i > left_bars else highs[i]
            right_max = highs[i + 1 : i + right_bars + 1].max() if i + right_bars < n else highs[i]
            prominence = min(left_max, right_max) - lows[i]
            prom_pct   = prominence / lows[i] * 100 if lows[i] > 0 else 0

            if prom_pct >= min_prominence_pct:
                pivots.append(Pivot(
                    bar_index  = i,
                    timestamp  = df.index[i],
                    price      = lows[i],
                    is_high    = False,
                    prominence = prominence,
                    volume     = volumes[i],
                ))

    return sorted(pivots, key=lambda p: p.bar_index)


# ──────────────────────────────────────────────────────────────────────────────
# CLASSIFICAZIONE HH / LH / HL / LL
# ──────────────────────────────────────────────────────────────────────────────

def classify_pivots(pivots: list[Pivot]) -> list[Pivot]:
    """
    Classifica ogni pivot come HH/LH (per i pivot high) o HL/LL (per i pivot low)
    confrontandolo con il pivot dello stesso tipo immediatamente precedente.

    HH: pivot high > pivot high precedente  → forza bullish
    LH: pivot high < pivot high precedente  → debolezza (possibile inversione)
    HL: pivot low  > pivot low precedente   → forza bullish
    LL: pivot low  < pivot low precedente   → forza bearish
    """
    highs = [p for p in pivots if p.is_high]
    lows  = [p for p in pivots if not p.is_high]

    # Classifica i pivot high
    for i, ph in enumerate(highs):
        if i == 0:
            ph.label = SwingLabel.HH  # primo pivot: label di default
        else:
            prev = highs[i - 1]
            ph.label = SwingLabel.HH if ph.price > prev.price else SwingLabel.LH

    # Classifica i pivot low
    for i, pl in enumerate(lows):
        if i == 0:
            pl.label = SwingLabel.HL
        else:
            prev = lows[i - 1]
            pl.label = SwingLabel.HL if pl.price > prev.price else SwingLabel.LL

    return pivots


# ──────────────────────────────────────────────────────────────────────────────
# TREND STATE — macchina a stati basata sulla struttura
# ──────────────────────────────────────────────────────────────────────────────

def compute_trend_state(pivots: list[Pivot]) -> TrendState:
    """
    Determina il trend corrente dall'ultimo pivot:
    - Uptrend   = ultimo HH > penultimo HH E ultimo HL > penultimo HL
    - Downtrend = ultimo LH < penultimo LH E ultimo LL < penultimo LL
    - Undefined = struttura non chiara
    """
    highs = [p for p in pivots if p.is_high]
    lows  = [p for p in pivots if not p.is_high]

    if len(highs) >= 2 and len(lows) >= 2:
        hh_seq = highs[-1].label == SwingLabel.HH
        hl_seq = lows[-1].label  == SwingLabel.HL
        lh_seq = highs[-1].label == SwingLabel.LH
        ll_seq = lows[-1].label  == SwingLabel.LL

        if hh_seq and hl_seq:
            return TrendState.UPTREND
        if lh_seq and ll_seq:
            return TrendState.DOWNTREND

    return TrendState.UNDEFINED


# ──────────────────────────────────────────────────────────────────────────────
# RILEVAMENTO BOS e CHoCH
# ──────────────────────────────────────────────────────────────────────────────

def detect_structure_events(df: pd.DataFrame,
                             pivots: list[Pivot],
                             require_close: bool = True) -> list[StructureSignal]:
    """
    Scansiona barra per barra e rileva rotture strutturali.

    Args:
        df:            DataFrame OHLCV con indicatori
        pivots:        Lista pivot classificati
        require_close: True = richiede chiusura oltre il livello (più robusto)
                       False = basta che il prezzo tocchi il livello (più reattivo)

    Returns:
        Lista di StructureSignal ordinati per bar_index
    """
    closes       = df["close"].values
    highs        = df["high"].values
    lows         = df["low"].values
    vol_ratio    = df["volume_ratio"].values if "volume_ratio" in df.columns else np.ones(len(df))
    n            = len(df)
    signals      = []

    # Separa pivot high e low e ordina per bar_index
    pivot_highs = sorted([p for p in pivots if p.is_high],     key=lambda p: p.bar_index)
    pivot_lows  = sorted([p for p in pivots if not p.is_high], key=lambda p: p.bar_index)

    if not pivot_highs or not pivot_lows:
        return signals

    # Per ogni barra, tieni traccia dei pivot "attivi" (già confermati prima di i)
    # e del trend corrente
    ph_idx = 0   # puntatore ai pivot high
    pl_idx = 0   # puntatore ai pivot low

    # Pivot attivi: ultimo high e ultimo low confermati prima della barra corrente
    active_high: Optional[Pivot] = None
    active_low:  Optional[Pivot] = None

    # Struttura dei pivot precedenti per classificazione BOS/CHoCH
    prev_high: Optional[Pivot] = None
    prev_low:  Optional[Pivot] = None

    current_trend = TrendState.UNDEFINED

    for i in range(1, n):
        ts = df.index[i]

        # Aggiorna pivot attivi: includi tutti i pivot confermati prima di i
        while ph_idx < len(pivot_highs) and pivot_highs[ph_idx].bar_index < i:
            prev_high   = active_high
            active_high = pivot_highs[ph_idx]
            ph_idx += 1

        while pl_idx < len(pivot_lows) and pivot_lows[pl_idx].bar_index < i:
            prev_low   = active_low
            active_low = pivot_lows[pl_idx]
            pl_idx += 1

        if active_high is None or active_low is None:
            continue

        price  = closes[i] if require_close else highs[i]
        price_l = closes[i] if require_close else lows[i]

        # ── Rottura sopra l'ultimo pivot HIGH
        if price > active_high.price:
            if current_trend == TrendState.DOWNTREND:
                # Uptrend inverso: CHoCH bullish
                event = StructureEvent.CHOCH_UP
            else:
                # Continuazione o partenza uptrend: BOS bullish
                event = StructureEvent.BOS_UP

            signals.append(StructureSignal(
                bar_index    = i,
                timestamp    = ts,
                event        = event,
                price        = closes[i],
                level        = active_high.price,
                prev_pivot   = active_high,
                trend_before = current_trend,
                volume_ratio = float(vol_ratio[i]),
            ))
            current_trend = TrendState.UPTREND

        # ── Rottura sotto l'ultimo pivot LOW
        elif price_l < active_low.price:
            if current_trend == TrendState.UPTREND:
                # Downtrend inverso: CHoCH bearish
                event = StructureEvent.CHOCH_DOWN
            else:
                # Continuazione o partenza downtrend: BOS bearish
                event = StructureEvent.BOS_DOWN

            signals.append(StructureSignal(
                bar_index    = i,
                timestamp    = ts,
                event        = event,
                price        = closes[i],
                level        = active_low.price,
                prev_pivot   = active_low,
                trend_before = current_trend,
                volume_ratio = float(vol_ratio[i]),
            ))
            current_trend = TrendState.DOWNTREND

    return signals


# ──────────────────────────────────────────────────────────────────────────────
# STRUTTURA CORRENTE — snapshot dello stato attuale
# ──────────────────────────────────────────────────────────────────────────────

def get_current_structure(pivots: list[Pivot],
                          signals: list[StructureSignal]) -> dict:
    """
    Restituisce uno snapshot della struttura di mercato corrente:
    trend, ultimo swing high/low, prossimi livelli chiave.
    """
    if not pivots:
        return {"trend": "UNDEFINED"}

    highs = sorted([p for p in pivots if p.is_high],     key=lambda p: p.bar_index)
    lows  = sorted([p for p in pivots if not p.is_high], key=lambda p: p.bar_index)

    last_high = highs[-1]  if highs else None
    last_low  = lows[-1]   if lows  else None
    last_sig  = signals[-1] if signals else None
    trend     = compute_trend_state(pivots)

    # Sequenza degli ultimi 4 pivot (per visualizzazione)
    recent = sorted(pivots, key=lambda p: p.bar_index)[-6:]

    # Struttura intatta: uptrend = nessun LL dopo l'ultimo HL, downtrend = nessun HH dopo l'ultimo LH
    structure_intact = True
    if trend == TrendState.UPTREND and lows:
        recent_lows = [p for p in lows if p.bar_index > lows[-2].bar_index] if len(lows) >= 2 else []
        structure_intact = not any(p.label == SwingLabel.LL for p in recent_lows)
    elif trend == TrendState.DOWNTREND and highs:
        recent_highs = [p for p in highs if p.bar_index > highs[-2].bar_index] if len(highs) >= 2 else []
        structure_intact = not any(p.label == SwingLabel.HH for p in recent_highs)

    return {
        "trend":            trend.value,
        "structure_intact": structure_intact,
        "last_high":        last_high.to_dict()  if last_high else None,
        "last_low":         last_low.to_dict()   if last_low  else None,
        "last_signal":      last_sig.to_dict()   if last_sig  else None,
        "recent_pivots":    [p.to_dict() for p in recent],
        "n_pivots_total":   len(pivots),
        "n_signals_total":  len(signals),
    }


# ──────────────────────────────────────────────────────────────────────────────
# ANALISI MULTI-TIMEFRAME
# ──────────────────────────────────────────────────────────────────────────────

def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggrega dati daily in weekly (open=Mon, high=max, low=min, close=Fri, volume=sum).
    """
    weekly = df.resample("W-FRI").agg({
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    }).dropna()
    return weekly


def mtf_structure_confluence(daily_df: pd.DataFrame,
                              daily_pivots: list[Pivot],
                              daily_signals: list[StructureSignal],
                              left_bars_weekly: int = 3,
                              right_bars_weekly: int = 3,
                              min_prom_weekly: float = 2.0) -> dict:
    """
    Analisi della struttura su due TF: daily e weekly.
    Restituisce un dizionario di confluenza.

    Logica:
      - Trend weekly = macro filtro (deve essere allineato)
      - Trend daily  = segnale operativo
      - Confluenza LONG  = weekly UPTREND + daily UPTREND o CHoCH_UP
      - Confluenza SHORT = weekly DOWNTREND + daily DOWNTREND o CHoCH_DOWN
    """
    weekly_df     = resample_to_weekly(daily_df)
    if "volume" not in weekly_df.columns:
        weekly_df["volume"] = 1.0
    weekly_df["volume_ratio"] = 1.0  # non rilevante su weekly

    weekly_pivots  = find_pivots(weekly_df, left_bars_weekly, right_bars_weekly, min_prom_weekly)
    weekly_pivots  = classify_pivots(weekly_pivots)
    weekly_signals = detect_structure_events(weekly_df, weekly_pivots)

    weekly_trend = compute_trend_state(weekly_pivots)
    daily_trend  = compute_trend_state(daily_pivots)

    # Ultimo segnale daily rilevante
    last_daily_sig = daily_signals[-1] if daily_signals else None

    # Confluenza
    long_confluence  = (
        weekly_trend == TrendState.UPTREND and
        (daily_trend == TrendState.UPTREND or
         (last_daily_sig and last_daily_sig.event == StructureEvent.CHOCH_UP))
    )
    short_confluence = (
        weekly_trend == TrendState.DOWNTREND and
        (daily_trend == TrendState.DOWNTREND or
         (last_daily_sig and last_daily_sig.event == StructureEvent.CHOCH_DOWN))
    )

    weekly_struct = get_current_structure(weekly_pivots, weekly_signals)
    daily_struct  = get_current_structure(daily_pivots, daily_signals)

    return {
        "weekly_trend":      weekly_trend.value,
        "daily_trend":       daily_trend.value,
        "long_confluence":   long_confluence,
        "short_confluence":  short_confluence,
        "weekly_structure":  weekly_struct,
        "daily_structure":   daily_struct,
        "weekly_n_pivots":   len(weekly_pivots),
        "daily_n_pivots":    len(daily_pivots),
    }


# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE COMPLETA PER UN SINGOLO TICKER
# ──────────────────────────────────────────────────────────────────────────────

def analyze(df: pd.DataFrame,
            left_bars: int = 5,
            right_bars: int = 5,
            min_prominence_pct: float = 1.0,
            require_close: bool = True,
            include_weekly: bool = True) -> dict:
    """
    Pipeline completa su un singolo ticker.

    Args:
        df:  DataFrame OHLCV daily con DatetimeIndex e colonna volume_ratio
             (calcolata da indicators.compute_all)

    Returns:
        Dizionario con pivots, signals, structure, mtf_confluence
    """
    pivots  = find_pivots(df, left_bars, right_bars, min_prominence_pct)
    pivots  = classify_pivots(pivots)
    signals = detect_structure_events(df, pivots, require_close)
    current = get_current_structure(pivots, signals)

    result = {
        "pivots":    [p.to_dict() for p in pivots],
        "signals":   [s.to_dict() for s in signals],
        "structure": current,
    }

    if include_weekly and len(df) >= 30:
        mtf = mtf_structure_confluence(df, pivots, signals)
        result["mtf"] = mtf

    return result


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    np.random.seed(42)
    n      = 252
    dates  = pd.date_range("2023-01-01", periods=n, freq="B")
    # Trend su con correzioni
    close  = 100 + np.cumsum(np.random.randn(n) * 1.2 + 0.1)
    high   = close + np.abs(np.random.randn(n) * 0.8)
    low    = close - np.abs(np.random.randn(n) * 0.8)
    volume = np.random.randint(500_000, 5_000_000, n).astype(float)

    df = pd.DataFrame({
        "open": close, "high": high, "low": low,
        "close": close, "volume": volume
    }, index=dates)
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

    result = analyze(df, left_bars=5, right_bars=5, min_prominence_pct=0.8)
    print(f"✓ analyze: {result['structure']['n_pivots_total']} pivot, "
          f"{result['structure']['n_signals_total']} segnali strutturali")
    print(f"  Trend daily:  {result['structure']['trend']}")
    print(f"  Struttura intatta: {result['structure']['structure_intact']}")
    if "mtf" in result:
        print(f"  Trend weekly: {result['mtf']['weekly_trend']}")
        print(f"  Long confluence: {result['mtf']['long_confluence']}")
