"""
Structure Detection - Pivot Points, Swing Classification, ChoCH/BOS Detection

Architecture:
  1. Pivot Detection: Identify swing highs/lows using scipy.signal.argrelextrema
  2. Swing Classification: Classify as HH/LH/HL/LL (Higher High, Lower High, etc.)
  3. ChoCH Detection: Change of Character (reversal point crossing)
  4. BOS Detection: Break of Structure (structure invalidation)
  5. Support/Resistance: Key levels for entries/stops
"""

import pandas as pd
import numpy as np
from scipy import signal
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class Pivot:
    """Single pivot point (swing high or low)"""
    index: int
    date: Any  # datetime or similar
    value: float
    type: str  # 'high' or 'low'
    order: int  # Sequential order (0 = oldest)


@dataclass
class SwingStructure:
    """Container for identified swing structure"""
    pivots: List[Pivot]  # All identified pivots (chronological)
    formation: str  # 'HH/LH' (downtrend), 'LH/LL' (uptrend), 'HH/HL' (choppy), etc.
    direction: int  # 1 (bullish: LL/LH), -1 (bearish: HH/LH), 0 (choppy)
    context: str  # Descriptive text


class PivotFinder:
    """Detect swing highs and lows using local extrema"""
    
    def __init__(self, min_lookback: int = 2, min_bar_height: float = 0.01):
        """
        Initialize pivot finder
        
        Args:
            min_lookback: Bars on each side to confirm pivot (default 2 = 5-bar pivot)
            min_bar_height: Minimum % change to qualify as pivot (eliminates noise)
        """
        self.min_lookback = min_lookback
        self.min_bar_height = min_bar_height
    
    def find_pivots(self, df: pd.DataFrame) -> Tuple[List[Pivot], List[Pivot]]:
        """
        Find swing highs and lows in OHLCV data
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
        
        Returns:
            (swing_highs, swing_lows) - lists of Pivot objects, chronological order
        """
        highs = df['high'].values
        lows = df['low'].values
        dates = df.get('date', df.index).values
        
        # Find local maxima and minima
        high_indices = signal.argrelextrema(highs, np.greater, order=self.min_lookback)[0]
        low_indices = signal.argrelextrema(lows, np.less, order=self.min_lookback)[0]
        
        # Filter by minimum height to avoid noise
        close_vals = df['close'].values
        
        swing_highs = []
        for idx in high_indices:
            pivot_height = (highs[idx] - close_vals[idx]) / close_vals[idx]
            if abs(pivot_height) >= self.min_bar_height:
                swing_highs.append(Pivot(
                    index=idx,
                    date=dates[idx],
                    value=highs[idx],
                    type='high',
                    order=len(swing_highs)
                ))
        
        swing_lows = []
        for idx in low_indices:
            pivot_height = (close_vals[idx] - lows[idx]) / close_vals[idx]
            if abs(pivot_height) >= self.min_bar_height:
                swing_lows.append(Pivot(
                    index=idx,
                    date=dates[idx],
                    value=lows[idx],
                    type='low',
                    order=len(swing_lows)
                ))
        
        return swing_highs, swing_lows
    
    def get_last_n_pivots(
        self,
        df: pd.DataFrame,
        n: int = 4,
        only_type: str = None
    ) -> List[Pivot]:
        """
        Get last N pivots (most recent first)
        
        Args:
            df: OHLCV DataFrame
            n: Number of pivots to return
            only_type: Filter to 'high' or 'low' only (None = both)
        
        Returns:
            Last N pivots, reverse chronological order
        """
        highs, lows = self.find_pivots(df)
        
        if only_type == 'high':
            combined = highs
        elif only_type == 'low':
            combined = lows
        else:
            # Merge and sort by index
            combined = sorted(highs + lows, key=lambda p: p.index)
        
        return combined[-n:][::-1]  # Last N, reversed


class SwingClassifier:
    """Classify swings as HH/LH/HL/LL formations"""
    
    def __init__(self):
        self.pivot_finder = PivotFinder()
    
    def classify_structure(self, df: pd.DataFrame, include_extended: bool = False) -> SwingStructure:
        """
        Classify overall swing structure
        
        Args:
            df: OHLCV DataFrame
            include_extended: Include extended history (slower but more context)
        
        Returns:
            SwingStructure with formation, direction, pivots
        
        Logic:
          Last 2 swings determine structure:
            LL/LH → uptrend (bullish, direction=1)
            HH/LH → downtrend (bearish, direction=-1)
            HH/HL or HL/LL → choppy/reversal (direction=0)
        """
        highs, lows = self.pivot_finder.find_pivots(df)
        
        if not highs or not lows:
            return SwingStructure(
                pivots=[],
                formation="INSUFFICIENT_DATA",
                direction=0,
                context="Not enough pivots to determine structure"
            )
        
        # Merge pivots chronologically
        all_pivots = sorted(highs + lows, key=lambda p: p.index)
        
        if len(all_pivots) < 2:
            return SwingStructure(
                pivots=all_pivots,
                formation="INSUFFICIENT_DATA",
                direction=0,
                context="Only 1 pivot found"
            )
        
        # Get last 2 swings to determine formation
        recent_2 = all_pivots[-2:]
        
        p1_type = recent_2[0].type
        p2_type = recent_2[1].type
        p1_val = recent_2[0].value
        p2_val = recent_2[1].value
        
        # Determine formation and direction
        if p1_type == 'high' and p2_type == 'low':
            # High then Low
            if p2_val > recent_2[0].value:  # current low > previous high = HH pattern setup
                formation = "HH_SETUP"
                direction = 1  # Bullish bias
                context = "Lower high but higher low = Bullish divergence (ascending)"
            else:
                formation = "HL"
                direction = 0
                context = "Choppy: High then Lower Low"
        
        elif p1_type == 'low' and p2_type == 'high':
            # Low then High
            if p2_val > recent_2[0].value:  # current high > previous low = bullish
                formation = "LL_LH"
                direction = 1
                context = "Higher lows and higher highs = Uptrend (bullish)"
            else:
                formation = "LH"
                direction = -1
                context = "Lower high after low = Potential reversal (bearish)"
        
        elif p1_type == 'high' and p2_type == 'high':
            # Two highs in sequence
            if p2_val > p1_val:
                formation = "HH"
                direction = 1
                context = "Higher highs = Uptrend continuation (bullish)"
            else:
                formation = "HH_LOWER"
                direction = -1
                context = "Lower highs = Downtrend (bearish)"
        
        else:  # two lows
            # Two lows in sequence
            if p2_val > p1_val:
                formation = "LL_HIGHER"
                direction = 1
                context = "Higher lows = Uptrend (bullish)"
            else:
                formation = "LL"
                direction = -1
                context = "Lower lows = Downtrend (bearish)"
        
        return SwingStructure(
            pivots=all_pivots,
            formation=formation,
            direction=direction,
            context=context
        )
    
    def detect_choch(self, df: pd.DataFrame, lookback: int = 50) -> Tuple[bool, str]:
        """
        Detect Change of Character (ChoCH) - reversal point crossing
        
        Args:
            df: OHLCV DataFrame
            lookback: Bars to examine for ChoCH
        
        Returns:
            (has_choch, reason_string)
        
        Logic:
          Uptrend ChoCH = break of recent swing low
          Downtrend ChoCH = break of recent swing high
        """
        recent_df = df.tail(lookback)
        structure = self.classify_structure(recent_df)
        
        if not structure.pivots or len(structure.pivots) < 2:
            return False, "Insufficient pivots for ChoCH detection"
        
        # Find the key structural level
        recent_pivots = structure.pivots[-3:] if len(structure.pivots) >= 3 else structure.pivots
        
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Uptrend: ChoCH if low is broken
        if structure.direction == 1:
            key_level = min(p.value for p in recent_pivots if p.type == 'low')
            has_choch = current_low < key_level
            
            if has_choch:
                return True, f"ChoCH DOWN: Broke swing low at {key_level:.2f} (current: {current_low:.2f})"
            else:
                return False, f"Uptrend intact: Low {current_low:.2f} > {key_level:.2f}"
        
        # Downtrend: ChoCH if high is broken
        elif structure.direction == -1:
            key_level = max(p.value for p in recent_pivots if p.type == 'high')
            has_choch = current_high > key_level
            
            if has_choch:
                return True, f"ChoCH UP: Broke swing high at {key_level:.2f} (current: {current_high:.2f})"
            else:
                return False, f"Downtrend intact: High {current_high:.2f} < {key_level:.2f}"
        
        else:
            return False, "Structure is choppy/unclear - ChoCH detection skipped"
    
    def detect_bos(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Detect Break of Structure (BOS) - invalidation of last swing
        
        Returns:
            (has_bos, reason_string)
        
        Logic:
          BOS = liquidity grab in opposite direction before continuing
          Example: uptrend high → pullback low → then break previous high = BOS
        """
        if len(df) < 5:
            return False, "Insufficient data for BOS detection"
        
        structure = self.classify_structure(df)
        
        if not structure.pivots or len(structure.pivots) < 2:
            return False, "Insufficient pivots for BOS detection"
        
        # Get last 3 pivots
        recent = structure.pivots[-3:] if len(structure.pivots) >= 3 else structure.pivots
        
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Uptrend BOS: Pulled back low, now breaking previous high
        if structure.direction == 1 and len(recent) >= 2:
            prev_high = max(p.value for p in recent if p.type == 'high')
            prev_low = min(p.value for p in recent if p.type == 'low')
            
            # Check if we broke high after going to low
            if current_high > prev_high and (df['low'].iloc[-5:].min() < prev_low):
                return True, f"BOS UP: Liquidity grab to {prev_low:.2f}, now > {prev_high:.2f}"
            else:
                return False, f"No uptrend BOS yet"
        
        # Downtrend BOS: Pulled back high, now breaking previous low
        elif structure.direction == -1 and len(recent) >= 2:
            prev_low = min(p.value for p in recent if p.type == 'low')
            prev_high = max(p.value for p in recent if p.type == 'high')
            
            # Check if we broke low after going to high
            if current_low < prev_low and (df['high'].iloc[-5:].max() > prev_high):
                return True, f"BOS DOWN: Liquidity grab to {prev_high:.2f}, now < {prev_low:.2f}"
            else:
                return False, f"No downtrend BOS yet"
        
        else:
            return False, "Structure is unclear for BOS detection"
    
    def get_key_levels(self, df: pd.DataFrame, n_levels: int = 3) -> Dict[str, List[float]]:
        """
        Extract key support/resistance levels from structure
        
        Returns:
            {
                'resistances': [r1, r2, r3],  # High to low
                'supports': [s1, s2, s3]       # Low to high
            }
        """
        highs, lows = self.pivot_finder.find_pivots(df)
        
        resistance_levels = sorted([p.value for p in highs], reverse=True)[:n_levels]
        support_levels = sorted([p.value for p in lows])[:n_levels]
        
        return {
            'resistances': resistance_levels,
            'supports': support_levels
        }


# ==================== EXAMPLE USAGE ====================

def example_structure_detection():
    """Example: Detect structure and pivots"""
    import yfinance as yf
    
    # Fetch data
    df = yf.download("SPY", start="2024-01-01", end="2025-02-01", progress=False)
    df = df.reset_index()
    df.columns = df.columns.str.lower()
    
    classifier = SwingClassifier()
    
    # Get structure
    structure = classifier.classify_structure(df)
    print(f"\n📊 STRUCTURE ANALYSIS")
    print(f"  Formation: {structure.formation}")
    print(f"  Direction: {'🔺 Bullish' if structure.direction == 1 else '🔻 Bearish' if structure.direction == -1 else '➡️ Choppy'}")
    print(f"  Context: {structure.context}")
    print(f"  Total Pivots: {len(structure.pivots)}")
    
    # Last 4 pivots
    print(f"\n📍 Last 4 Pivots:")
    for p in structure.pivots[-4:]:
        type_emoji = "⬆️" if p.type == "high" else "⬇️"
        print(f"  {type_emoji} {p.date}: {p.value:.2f} ({p.type})")
    
    # ChoCH
    choch, choch_reason = classifier.detect_choch(df)
    print(f"\n🔄 ChoCH: {'✓ YES' if choch else '✗ NO'}")
    print(f"  {choch_reason}")
    
    # BOS
    bos, bos_reason = classifier.detect_bos(df)
    print(f"\n💥 BOS: {'✓ YES' if bos else '✗ NO'}")
    print(f"  {bos_reason}")
    
    # Key levels
    levels = classifier.get_key_levels(df)
    print(f"\n🎯 Key Levels:")
    print(f"  Resistance: {[f'{r:.2f}' for r in levels['resistances']]}")
    print(f"  Support: {[f'{s:.2f}' for s in levels['supports']]}")


if __name__ == "__main__":
    example_structure_detection()
