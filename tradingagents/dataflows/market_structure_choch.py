"""
market_structure_choch.py
═════════════════════════════════════════════════════════════════════════════
Smart Market Structure Detection — CHoCH, BOS, HH/LH/HL/LL, MTF Confluence

LOGICA:
  Identifica pivot high/low → classifica in HH/LH/HL/LL → rileva BOS/CHoCH
  - BOS = continuazione trend (rompe livello strutturale precedente)
  - CHoCH = inversione trend (rompe supporto/resistenza counter-trend)
  - Confluenza MTF se weekly trend coincide con daily
────────────────────────────────────────────────────────────────────────────────
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


# ═════════════════════════════════════════════════════════════════════════════
# ENUMS E DATACLASSES
# ═════════════════════════════════════════════════════════════════════════════

class SwingLabel(str, Enum):
    HH = "HH"
    LH = "LH"  
    HL = "HL"
    LL = "LL"


class StructureEvent(str, Enum):
    BOS_UP     = "BOS_UP"      # Rompe HH → continuazione bullish
    BOS_DOWN   = "BOS_DOWN"    # Rompe LL → continuazione bearish
    CHOCH_UP   = "CHoCH_UP"    # Rompe LH → inversione bullish
    CHOCH_DOWN = "CHoCH_DOWN"  # Rompe HL → inversione bearish


class TrendState(str, Enum):
    UPTREND   = "UPTREND"
    DOWNTREND = "DOWNTREND"
    UNDEFINED = "UNDEFINED"


@dataclass
class Pivot:
    """Identifica un swing high o low locale"""
    bar_index:  int
    timestamp:  pd.Timestamp
    price:      float
    is_high:    bool                       # True=high, False=low
    label:      Optional[SwingLabel] = None
    prominence: float = 0.0
    volume:     float = 0.0

    @property
    def label_str(self) -> str:
        return self.label.value if self.label else "?"

    def to_dict(self) -> dict:
        return {
            "bar_index": self.bar_index,
            "timestamp": str(self.timestamp),
            "price": round(self.price, 6),
            "type": "HIGH" if self.is_high else "LOW",
            "label": self.label_str,
            "prominence": round(self.prominence, 6),
        }


@dataclass
class StructureSignal:
    """Segnale di rottura strutturale (BOS/CHoCH)"""
    bar_index:     int
    timestamp:     pd.Timestamp
    event:         StructureEvent
    price:         float           # close al momento della rottura
    level:         float           # livello strutturale rotto
    trend_before:  TrendState
    volume_ratio:  float = 1.0
    confluence:    bool = False    # True se MTF allineato

    @property
    def is_bullish(self) -> bool:
        return self.event in (StructureEvent.BOS_UP, StructureEvent.CHOCH_UP)

    @property
    def is_choch(self) -> bool:
        return self.event in (StructureEvent.CHOCH_UP, StructureEvent.CHOCH_DOWN)

    def to_dict(self) -> dict:
        return {
            "bar_index": self.bar_index,
            "timestamp": str(self.timestamp),
            "event": self.event.value,
            "price": round(self.price, 6),
            "level": round(self.level, 6),
            "trend_before": self.trend_before.value,
            "volume_ratio": round(self.volume_ratio, 2),
            "is_bullish": self.is_bullish,
            "is_choch": self.is_choch,
            "mtf_confluence": self.confluence,
        }


# ═════════════════════════════════════════════════════════════════════════════
# IDENTIFICAZIONE PIVOT
# ═════════════════════════════════════════════════════════════════════════════

def find_pivots(df: pd.DataFrame,
                left_bars: int = 5,
                right_bars: int = 5,
                min_prominence_pct: float = 1.0) -> List[Pivot]:
    """
    Identifica pivot high e low con finestra rolling.
    
    Un pivot high a barra i richiede:
      - high[i] == max(high[i-left : i+right+1])
      - prominence >= min_prominence_pct% del prezzo
      - Zero lookahead: confermato dopo right_bars barre
    
    Args:
        df: DataFrame OHLCV
        left_bars: barre a sinistra
        right_bars: barre a destra (ritardo conferma)
        min_prominence_pct: rilievo minimo come % del prezzo
    
    Returns:
        Lista di Pivot ordinati per bar_index
    """
    highs   = df["high"].values
    lows    = df["low"].values
    volumes = df["volume"].values if "volume" in df.columns else np.ones(len(df))
    n       = len(df)
    pivots  = []

    for i in range(left_bars, n - right_bars):
        # Pivot HIGH
        window_h = highs[i - left_bars : i + right_bars + 1]
        if highs[i] == window_h.max():
            left_min  = lows[i - left_bars : i].min() if i > left_bars else lows[i]
            right_min = lows[i + 1 : i + right_bars + 1].min() if i + right_bars < n else lows[i]
            prominence = highs[i] - max(left_min, right_min)
            prom_pct = prominence / highs[i] * 100 if highs[i] > 0 else 0

            if prom_pct >= min_prominence_pct:
                pivots.append(Pivot(
                    bar_index=i,
                    timestamp=df.index[i],
                    price=highs[i],
                    is_high=True,
                    prominence=prominence,
                    volume=volumes[i],
                ))

        # Pivot LOW
        window_l = lows[i - left_bars : i + right_bars + 1]
        if lows[i] == window_l.min():
            left_max = highs[i - left_bars : i].max() if i > left_bars else highs[i]
            right_max = highs[i + 1 : i + right_bars + 1].max() if i + right_bars < n else highs[i]
            prominence = min(left_max, right_max) - lows[i]
            prom_pct = prominence / lows[i] * 100 if lows[i] > 0 else 0

            if prom_pct >= min_prominence_pct:
                pivots.append(Pivot(
                    bar_index=i,
                    timestamp=df.index[i],
                    price=lows[i],
                    is_high=False,
                    prominence=prominence,
                    volume=volumes[i],
                ))

    return sorted(pivots, key=lambda p: p.bar_index)


# ═════════════════════════════════════════════════════════════════════════════
# CLASSIFICAZIONE HH/LH/HL/LL
# ═════════════════════════════════════════════════════════════════════════════

def classify_pivots(pivots: List[Pivot]) -> List[Pivot]:
    """
    Classifica pivot come HH/LH/HL/LL confrontandoli con il pivot 
    dello stesso tipo immediatamente precedente.
    
    HH: pivot_high > prev_pivot_high   → forza bullish
    LH: pivot_high < prev_pivot_high   → debolezza (possibile inversione)
    HL: pivot_low > prev_pivot_low     → forza bullish
    LL: pivot_low < prev_pivot_low     → forza bearish
    """
    highs = [p for p in pivots if p.is_high]
    lows = [p for p in pivots if not p.is_high]

    # Classifica high
    for i, p in enumerate(highs):
        if i == 0:
            p.label = SwingLabel.HH  # primo high = HH by default
        else:
            p.label = SwingLabel.HH if p.price > highs[i-1].price else SwingLabel.LH

    # Classifica low
    for i, p in enumerate(lows):
        if i == 0:
            p.label = SwingLabel.LL  # primo low = LL by default
        else:
            p.label = SwingLabel.HL if p.price > lows[i-1].price else SwingLabel.LL

    # Re-order tutti i pivot per bar_index
    all_pivots = highs + lows
    return sorted(all_pivots, key=lambda p: p.bar_index)


# ═════════════════════════════════════════════════════════════════════════════
# DETERMINAZIONE TREND
# ═════════════════════════════════════════════════════════════════════════════

def determine_trend(pivots: List[Pivot]) -> TrendState:
    """
    Determine il trend corrente basato sui pivot ultimi.
    
    UPTREND:   sequenza HH → HL
    DOWNTREND: sequenza LH → LL
    UNDEFINED: non abbastanza pivot
    """
    if len(pivots) < 2:
        return TrendState.UNDEFINED

    recent = pivots[-2:]  # ultimi 2 pivot
    
    if recent[0].is_high and not recent[1].is_high:  # High poi Low
        if recent[1].label in (SwingLabel.HL, SwingLabel.LH):
            return TrendState.UPTREND if recent[1].label == SwingLabel.HL else TrendState.UNDEFINED
    elif not recent[0].is_high and recent[1].is_high:  # Low poi High
        if recent[1].label in (SwingLabel.HH, SwingLabel.LH):
            return TrendState.UPTREND if recent[1].label == SwingLabel.HH else TrendState.DOWNTREND

    return TrendState.UNDEFINED


# ═════════════════════════════════════════════════════════════════════════════
# RILEVAZIONE BOS/CHoCH
# ═════════════════════════════════════════════════════════════════════════════

def detect_structure_breaks(df: pd.DataFrame,
                            pivots: List[Pivot]) -> List[StructureSignal]:
    """
    Rileva BOS e CHoCH comparando il close corrente con livelli strutturali.
    
    In UPTREND (HH→HL):
      - BOS_UP:     close > HH → continuazione
      - CHoCH_DOWN: close < HL → inversione
    
    In DOWNTREND (LH→LL):
      - BOS_DOWN:   close < LL → continuazione
      - CHoCH_UP:   close > LH → inversione
    
    Returns:
        Lista di StructureSignal cronologicamente ordinate
    """
    breaks = []
    highs = [p for p in pivots if p.is_high]
    lows = [p for p in pivots if not p.is_high]

    # Livelli strutturali
    last_hh = highs[-1].price if highs else None
    last_hh_idx = highs[-1].bar_index if highs else None
    last_lh = highs[-2].price if len(highs) >= 2 else None

    last_ll = lows[-1].price if lows else None
    last_ll_idx = lows[-1].bar_index if lows else None
    last_hl = lows[-2].price if len(lows) >= 2 else None

    trend = determine_trend(pivots)

    # Scorri il DataFrame cercando rotture
    for i in range(last_hh_idx or 0, len(df)):
        close = df["close"].iloc[i]
        timestamp = df.index[i]
        volume_ratio = df["volume_ratio"].iloc[i] if "volume_ratio" in df.columns else 1.0

        # UPTREND: cerca BOS_UP e CHoCH_DOWN
        if trend == TrendState.UPTREND:
            if last_hh and close > last_hh and i > last_hh_idx:
                breaks.append(StructureSignal(
                    bar_index=i,
                    timestamp=timestamp,
                    event=StructureEvent.BOS_UP,
                    price=close,
                    level=last_hh,
                    trend_before=trend,
                    volume_ratio=volume_ratio,
                ))
                trend = TrendState.UPTREND

            if last_hl and close < last_hl:
                breaks.append(StructureSignal(
                    bar_index=i,
                    timestamp=timestamp,
                    event=StructureEvent.CHOCH_DOWN,
                    price=close,
                    level=last_hl,
                    trend_before=trend,
                    volume_ratio=volume_ratio,
                ))
                trend = TrendState.DOWNTREND

        # DOWNTREND: cerca BOS_DOWN e CHoCH_UP
        elif trend == TrendState.DOWNTREND:
            if last_ll and close < last_ll and i > last_ll_idx:
                breaks.append(StructureSignal(
                    bar_index=i,
                    timestamp=timestamp,
                    event=StructureEvent.BOS_DOWN,
                    price=close,
                    level=last_ll,
                    trend_before=trend,
                    volume_ratio=volume_ratio,
                ))
                trend = TrendState.DOWNTREND

            if last_lh and close > last_lh:
                breaks.append(StructureSignal(
                    bar_index=i,
                    timestamp=timestamp,
                    event=StructureEvent.CHOCH_UP,
                    price=close,
                    level=last_lh,
                    trend_before=trend,
                    volume_ratio=volume_ratio,
                ))
                trend = TrendState.UPTREND

    return breaks


# ═════════════════════════════════════════════════════════════════════════════
# ANALISI COMPLETA
# ═════════════════════════════════════════════════════════════════════════════

def analyze(df: pd.DataFrame,
            left_bars: int = 5,
            right_bars: int = 5,
            include_weekly: bool = False) -> dict:
    """
    Analisi completa della struttura di mercato.
    
    Args:
        df: DataFrame OHLCV (daily)
        left_bars, right_bars: parametri pivot detection
        include_weekly: se True, applica anche a weekly data
    
    Returns:
        dict con keys:
          - pivots_daily: Lista [Pivot]
          - trend_daily: TrendState
          - breaks_daily: Lista [StructureSignal]
          - mtf: dict con weekly data (se include_weekly=True)
    """
    # Daily
    pivots_daily = find_pivots(df, left_bars, right_bars)
    pivots_daily = classify_pivots(pivots_daily)
    trend_daily = determine_trend(pivots_daily)
    breaks_daily = detect_structure_breaks(df, pivots_daily)

    result = {
        "pivots_daily": pivots_daily,
        "trend_daily": trend_daily,
        "breaks_daily": breaks_daily,
    }

    # Weekly (if includes_weekly)
    if include_weekly and len(df) >= 252:  # almeno 1 anno di dati daily
        weekly_data = df.iloc[::5].copy()  # sampla ogni 5 giorni (~1 settimana)
        pivots_weekly = find_pivots(weekly_data, left_bars, right_bars)
        pivots_weekly = classify_pivots(pivots_weekly)
        trend_weekly = determine_trend(pivots_weekly)

        result.update({
            "pivots_weekly": pivots_weekly,
            "trend_weekly": trend_weekly,
            "mtf_confluence": trend_daily == trend_weekly,
        })

    return result


if __name__ == "__main__":
    print("✓ market_structure_choch.py loaded successfully")
    print("  Functions: find_pivots(), classify_pivots(), analyze(), detect_structure_breaks()")
