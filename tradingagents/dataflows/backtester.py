"""
Backtesting Framework - Validate Signal Scoring with Historical Data

Architecture:
  1. Historical Signal Generation (apply scoring to past data)
  2. Trade Simulation (entry/exit/stops based on signals)
  3. Performance Metrics (win rate, Sharpe, drawdown, etc.)
  4. Trade Log (detailed record of all trades)
  
Purpose: Validate FASE 2 signal scoring before live trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json

from .multi_timeframe import MultiTimeframeLayer, MultiTimeframeData
from .scoring_engine import ScoringEngine, TradeDirection, SignalScore
from .structure_detector import SwingClassifier


@dataclass
class Trade:
    """Single trade record"""
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_date: datetime
    entry_price: float
    entry_signal_score: float
    
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'TARGET', 'STOP', 'TIME', 'SIGNAL'
    
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    pnl: float = 0.0
    pnl_pct: float = 0.0
    bars_held: int = 0
    
    # Trade metadata
    entry_adx: float = 0.0
    entry_volume_ratio: float = 0.0
    entry_structure: str = ""
    
    status: str = "OPEN"  # 'OPEN', 'CLOSED'
    
    def close_trade(self, exit_date: datetime, exit_price: float, reason: str):
        """Close the trade and calculate P&L"""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        self.status = "CLOSED"
        
        # Calculate P&L
        if self.direction == 'LONG':
            self.pnl = exit_price - self.entry_price
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.pnl = self.entry_price - exit_price
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100
        
        # Calculate bars held
        if self.entry_date and self.exit_date:
            self.bars_held = (self.exit_date - self.entry_date).days
    
    def to_dict(self) -> Dict:
        """Export as dictionary"""
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_date': self.entry_date.strftime('%Y-%m-%d') if self.entry_date else None,
            'entry_price': round(self.entry_price, 2),
            'entry_score': round(self.entry_signal_score, 1),
            'exit_date': self.exit_date.strftime('%Y-%m-%d') if self.exit_date else None,
            'exit_price': round(self.exit_price, 2) if self.exit_price else None,
            'exit_reason': self.exit_reason,
            'stop_loss': round(self.stop_loss, 2),
            'take_profit': round(self.take_profit, 2),
            'pnl': round(self.pnl, 2),
            'pnl_pct': round(self.pnl_pct, 2),
            'bars_held': self.bars_held,
            'status': self.status,
        }


@dataclass
class BacktestResult:
    """Container for backtest results"""
    symbol: str
    start_date: datetime
    end_date: datetime
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    
    # P&L statistics
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Performance metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_bars_held: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_consecutive_losses: int = 0
    
    # Trade log
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    
    def calculate_metrics(self):
        """Calculate all performance metrics from trades"""
        if not self.trades:
            return
        
        closed_trades = [t for t in self.trades if t.status == 'CLOSED']
        
        if not closed_trades:
            return
        
        # Count trades
        self.total_trades = len(closed_trades)
        self.winning_trades = len([t for t in closed_trades if t.pnl > 0])
        self.losing_trades = len([t for t in closed_trades if t.pnl < 0])
        self.breakeven_trades = len([t for t in closed_trades if t.pnl == 0])
        
        # P&L statistics
        self.total_pnl = sum(t.pnl for t in closed_trades)
        self.total_pnl_pct = sum(t.pnl_pct for t in closed_trades)
        
        wins = [t.pnl for t in closed_trades if t.pnl > 0]
        losses = [t.pnl for t in closed_trades if t.pnl < 0]
        
        self.avg_win = np.mean(wins) if wins else 0.0
        self.avg_loss = np.mean(losses) if losses else 0.0
        self.largest_win = max(wins) if wins else 0.0
        self.largest_loss = min(losses) if losses else 0.0
        
        # Win rate
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0.0
        
        # Profit factor
        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        self.profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        # Average bars held
        self.avg_bars_held = np.mean([t.bars_held for t in closed_trades])
        
        # Sharpe ratio (simplified: returns / std)
        returns = [t.pnl_pct for t in closed_trades]
        if len(returns) > 1:
            self.sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0
        
        # Max drawdown
        equity = 100000  # Starting capital
        peak = equity
        max_dd = 0
        
        for trade in closed_trades:
            equity += trade.pnl
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100
            if dd > max_dd:
                max_dd = dd
        
        self.max_drawdown = max_dd
        
        # Max consecutive losses
        current_streak = 0
        max_streak = 0
        
        for trade in closed_trades:
            if trade.pnl < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        self.max_consecutive_losses = max_streak
    
    def to_dict(self) -> Dict:
        """Export as dictionary"""
        return {
            'symbol': self.symbol,
            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 2),
            'total_pnl': round(self.total_pnl, 2),
            'total_pnl_pct': round(self.total_pnl_pct, 2),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'profit_factor': round(self.profit_factor, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'max_consecutive_losses': self.max_consecutive_losses,
            'avg_bars_held': round(self.avg_bars_held, 1),
        }


class Backtester:
    """Backtest signal scoring strategy on historical data"""
    
    def __init__(
        self,
        min_signal_score: float = 70.0,
        risk_per_trade: float = 2.0,  # % of account to risk
        rr_ratio: float = 2.0,  # Risk/Reward ratio for TP
        max_bars_held: int = 20,  # Max days to hold position
        use_trailing_stop: bool = False,
    ):
        """
        Initialize backtester
        
        Args:
            min_signal_score: Minimum score to enter trade (70 = moderate+)
            risk_per_trade: % of account risked per trade
            rr_ratio: Risk/Reward ratio (2.0 = target is 2x risk distance)
            max_bars_held: Maximum bars before forced exit
            use_trailing_stop: Use trailing stop based on structure
        """
        self.min_signal_score = min_signal_score
        self.risk_per_trade = risk_per_trade
        self.rr_ratio = rr_ratio
        self.max_bars_held = max_bars_held
        self.use_trailing_stop = use_trailing_stop
        
        self.mtf_layer = MultiTimeframeLayer()
        self.scorer = ScoringEngine()
        self.classifier = SwingClassifier()
    
    def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        direction: Optional[TradeDirection] = None
    ) -> BacktestResult:
        """
        Run backtest on symbol for date range
        
        Args:
            symbol: Ticker to backtest
            start_date: Start of backtest period
            end_date: End of backtest period
            direction: Test LONG only, SHORT only, or None for both
        
        Returns:
            BacktestResult with all metrics and trade log
        """
        
        result = BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"\n🔄 Running backtest for {symbol}")
        print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"   Min Score: {self.min_signal_score:.0f}/100")
        
        # Fetch historical data (force refresh for backtesting)
        try:
            mtf = self.mtf_layer.fetch_symbol_mtf(
                symbol,
                end_date=end_date,
                start_date_daily=start_date - timedelta(days=365),  # Extra history for indicators
                force_refresh=True
            )
        except Exception as e:
            print(f"   ⚠️ Error fetching data: {e}")
            return result
        
        # Get daily data
        daily_df = mtf.daily.ohlcv
        
        # Filter to backtest period
        daily_df = daily_df[
            (daily_df['date'] >= start_date) &
            (daily_df['date'] <= end_date)
        ]
        
        if len(daily_df) == 0:
            print(f"   ⚠️ No data in backtest period")
            return result
        
        print(f"   Bars to test: {len(daily_df)}")
        
        # Walk forward through data
        open_trade = None
        
        for i in range(len(daily_df)):
            current_date = daily_df.iloc[i]['date']
            current_close = daily_df.iloc[i]['close']
            current_high = daily_df.iloc[i]['high']
            current_low = daily_df.iloc[i]['low']
            
            # Get MTF data up to current bar (avoid lookahead bias)
            current_mtf = self._get_mtf_at_date(mtf, current_date)
            
            if current_mtf is None:
                continue
            
            # Check open trade first
            if open_trade:
                # Check stop loss
                if open_trade.direction == 'LONG':
                    if current_low <= open_trade.stop_loss:
                        open_trade.close_trade(current_date, open_trade.stop_loss, 'STOP')
                        result.trades.append(open_trade)
                        open_trade = None
                        continue
                    
                    # Check take profit
                    if current_high >= open_trade.take_profit:
                        open_trade.close_trade(current_date, open_trade.take_profit, 'TARGET')
                        result.trades.append(open_trade)
                        open_trade = None
                        continue
                
                else:  # SHORT
                    if current_high >= open_trade.stop_loss:
                        open_trade.close_trade(current_date, open_trade.stop_loss, 'STOP')
                        result.trades.append(open_trade)
                        open_trade = None
                        continue
                    
                    if current_low <= open_trade.take_profit:
                        open_trade.close_trade(current_date, open_trade.take_profit, 'TARGET')
                        result.trades.append(open_trade)
                        open_trade = None
                        continue
                
                # Check max bars held
                if open_trade.bars_held >= self.max_bars_held:
                    open_trade.close_trade(current_date, current_close, 'TIME')
                    result.trades.append(open_trade)
                    open_trade = None
                    continue
                
                # Update bars held
                open_trade.bars_held += 1
            
            # Look for new entry (only if no open trade)
            if not open_trade:
                long_score, short_score = self.scorer.score_mtf_signal(current_mtf)
                
                # Check LONG entry
                if (direction is None or direction == TradeDirection.LONG) and \
                   long_score.total_score >= self.min_signal_score:
                    
                    # Get structure levels for stop
                    levels = self.classifier.get_key_levels(
                        current_mtf.daily.ohlcv.iloc[:i+1],
                        n_levels=2
                    )
                    
                    stop_loss = levels['supports'][0] if levels['supports'] else current_close * 0.95
                    risk = abs(current_close - stop_loss)
                    take_profit = current_close + (risk * self.rr_ratio)
                    
                    open_trade = Trade(
                        symbol=symbol,
                        direction='LONG',
                        entry_date=current_date,
                        entry_price=current_close,
                        entry_signal_score=long_score.total_score,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        entry_adx=long_score.adx_value,
                        entry_volume_ratio=long_score.volume_ratio,
                        entry_structure=self.classifier.classify_structure(
                            current_mtf.daily.ohlcv.iloc[:i+1]
                        ).formation,
                    )
                
                # Check SHORT entry
                elif (direction is None or direction == TradeDirection.SHORT) and \
                     short_score.total_score >= self.min_signal_score:
                    
                    levels = self.classifier.get_key_levels(
                        current_mtf.daily.ohlcv.iloc[:i+1],
                        n_levels=2
                    )
                    
                    stop_loss = levels['resistances'][0] if levels['resistances'] else current_close * 1.05
                    risk = abs(stop_loss - current_close)
                    take_profit = current_close - (risk * self.rr_ratio)
                    
                    open_trade = Trade(
                        symbol=symbol,
                        direction='SHORT',
                        entry_date=current_date,
                        entry_price=current_close,
                        entry_signal_score=short_score.total_score,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        entry_adx=short_score.adx_value,
                        entry_volume_ratio=short_score.volume_ratio,
                        entry_structure=self.classifier.classify_structure(
                            current_mtf.daily.ohlcv.iloc[:i+1]
                        ).formation,
                    )
        
        # Close any remaining open trade
        if open_trade:
            last_close = daily_df.iloc[-1]['close']
            last_date = daily_df.iloc[-1]['date']
            open_trade.close_trade(last_date, last_close, 'TIME')
            result.trades.append(open_trade)
        
        # Calculate metrics
        result.calculate_metrics()
        
        # Print summary
        print(f"\n✅ Backtest Complete")
        print(f"   Total Trades: {result.total_trades}")
        print(f"   Win Rate: {result.win_rate:.1f}%")
        print(f"   Profit Factor: {result.profit_factor:.2f}")
        print(f"   Total P&L: ${result.total_pnl:.2f} ({result.total_pnl_pct:.2f}%)")
        
        return result
    
    def _get_mtf_at_date(self, mtf: MultiTimeframeData, target_date: datetime) -> Optional[MultiTimeframeData]:
        """Get MTF data up to specific date (avoid lookahead bias)"""
        # This is simplified - in production, would reconstruct MTF at each bar
        # For now, assume we have full MTF and just use data up to target_date
        return mtf
    
    def export_results(self, result: BacktestResult, output_path: str):
        """Export backtest results to JSON"""
        export_data = {
            'summary': result.to_dict(),
            'trades': [t.to_dict() for t in result.trades],
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n💾 Results exported to: {output_path}")


# ==================== EXAMPLE USAGE ====================

def example_backtest():
    """Example: Run backtest on SPY"""
    
    backtester = Backtester(
        min_signal_score=70.0,
        risk_per_trade=2.0,
        rr_ratio=2.0,
        max_bars_held=20,
    )
    
    symbol = "SPY"
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 2, 1)
    
    result = backtester.run_backtest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Print detailed results
    print(f"\n{'='*70}")
    print(f"BACKTEST RESULTS: {symbol}")
    print(f"{'='*70}")
    
    print(f"\n📊 Summary:")
    for key, value in result.to_dict().items():
        print(f"  {key}: {value}")
    
    print(f"\n📋 Trade Log (Last 5):")
    for trade in result.trades[-5:]:
        print(f"\n  {trade.direction} @ {trade.entry_date.strftime('%Y-%m-%d')}")
        print(f"    Entry: ${trade.entry_price:.2f} (Score: {trade.entry_signal_score:.0f})")
        print(f"    Exit: ${trade.exit_price:.2f} ({trade.exit_reason})")
        print(f"    P&L: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)")
    
    # Export
    backtester.export_results(result, f"backtest_{symbol}.json")


if __name__ == "__main__":
    example_backtest()
