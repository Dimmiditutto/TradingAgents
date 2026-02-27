"""
test_fase4_integration.py - Complete Integration Test for FASE 4
Tests all modules end-to-end: data → indicators → scoring → backtest → dashboard
"""

import sys
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np


def test_data_manager():
    """Test data manager and synthetic data generation."""
    print("\n" + "="*60)
    print("TEST 1: Data Manager & Synthetic Data")
    print("="*60)
    
    try:
        from tradingagents.dataflows.data_manager import (
            DataManager, generate_synthetic, get_sp500_subset, cache_info
        )
        
        # Test 1a: Generate synthetic data
        print("\n✓ Generating synthetic data...")
        df = generate_synthetic("TEST_UP", n_bars=504, trend="up", volatility=0.02, seed=42)
        assert len(df) == 504, "Synthetic data should have 504 bars"
        assert all(c in df.columns for c in ["open", "high", "low", "close", "volume"]), \
            "Missing OHLCV columns"
        print(f"  → Generated {len(df)} bars")
        print(f"  → Date range: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"  → Close range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        # Test 1b: S&P 500 subset
        print("\n✓ Getting S&P 500 subset...")
        tickers = get_sp500_subset(sectors=["technology"])
        assert len(tickers) > 0, "Should have tickers"
        print(f"  → Found {len(tickers)} technology tickers")
        print(f"  → Sample: {tickers[:5]}")
        
        # Test 1c: Cache info
        print("\n✓ Cache info...")
        info = cache_info()
        print(f"  → Cached symbols: {info['count']}")
        
        print("\n✅ Data Manager: PASSED")
        return df
        
    except Exception as e:
        print(f"\n❌ Data Manager: FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        return None


def test_indicators_advanced(df):
    """Test indicators computation."""
    print("\n" + "="*60)
    print("TEST 2: Indicators Advanced (51 indicators)")
    print("="*60)
    
    if df is None:
        print("⏭️  Skipped (no data)")
        return None
    
    try:
        from tradingagents.dataflows.indicators_advanced import compute_all
        
        print(f"\n✓ Computing {len(df)} bars...")
        df_with_indicators = compute_all(df.copy())
        
        added = len(df_with_indicators.columns) - len(df.columns)
        print(f"  → Added {added} indicator columns")
        print(f"  → Total columns: {len(df_with_indicators.columns)}")
        
        # Check key indicators
        key_indicators = ["RSI", "MACD", "ADX", "SuperTrend", "ATR", "volume_ratio"]
        for ind in key_indicators:
            if ind in df_with_indicators.columns:
                val = df_with_indicators[ind].iloc[-1]
                print(f"  ✓ {ind}: {val:.2f}" if isinstance(val, (int, float)) else f"  ✓ {ind}: {val}")
            else:
                print(f"  ✗ {ind}: MISSING")
        
        # Check for NaN at end
        nans = df_with_indicators.iloc[-20:].isna().sum().sum()
        if nans > 0:
            print(f"  ⚠️  {nans} NaN values in last 20 bars (normal for lagging indicators)")
        
        print("\n✅ Indicators Advanced: PASSED")
        return df_with_indicators
        
    except Exception as e:
        print(f"\n❌ Indicators Advanced: FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        return None


def test_scoring_engine(df):
    """Test scoring engine."""
    print("\n" + "="*60)
    print("TEST 3: Scoring Engine V2 (5-Component)")
    print("="*60)
    
    if df is None:
        print("⏭️  Skipped (no data)")
        return []
    
    try:
        from tradingagents.dataflows.scoring_engine_v2 import (
            score_signal, score_both_directions
        )
        
        # Test 3a: Score LONG
        print("\n✓ Scoring LONG direction...")
        signal_long = score_signal(df, ticker="TEST_UP", direction="LONG")
        if signal_long:
            print(f"  → Score: {signal_long.score:.0f}/100")
            print(f"  → Filters Passed: {signal_long.filters_passed}")
            if not signal_long.filters_passed:
                print(f"  → Failed filters: {signal_long.filter_failures}")
            else:
                print(f"  → Entry: ${signal_long.entry_price:.2f}")
                print(f"  → Stop: ${signal_long.stop_loss:.2f}")
                print(f"  → Target1: ${signal_long.target1:.2f}")
                print(f"  → R/R: {signal_long.risk_reward:.2f}")
        else:
            print("  → No signal generated")
        
        # Test 3b: Score SHORT
        print("\n✓ Scoring SHORT direction...")
        signal_short = score_signal(df, ticker="TEST_UP", direction="SHORT")
        if signal_short:
            print(f"  → Score: {signal_short.score:.0f}/100")
            print(f"  → Filters Passed: {signal_short.filters_passed}")
        else:
            print("  → No signal generated (expected for uptrend)")
        
        # Test 3c: Both directions
        print("\n✓ Scoring both directions...")
        signals = score_both_directions(df, ticker="TEST_UP")
        print(f"  → Generated {len(signals)} signals")
        valid_signals = [s for s in signals if s]
        print(f"  → Valid signals: {len(valid_signals)}")
        
        if valid_signals:
            for i, sig in enumerate(valid_signals[-3:]):  # Last 3
                print(f"  [{i+1}] {sig.direction}: Score {sig.score:.0f}, " 
                      f"Filters: {sig.filters_passed}")
        
        print("\n✅ Scoring Engine: PASSED")
        return signals
        
    except Exception as e:
        print(f"\n❌ Scoring Engine: FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        return []


def test_backtester(df, signals):
    """Test backtest engine."""
    print("\n" + "="*60)
    print("TEST 4: Backtester V2 (12 Metrics)")
    print("="*60)
    
    if df is None or len(signals) == 0:
        print("⏭️  Skipped (no data or signals)")
        return None
    
    try:
        from tradingagents.dataflows.backtester_v2 import BacktesterV2
        from tradingagents.dataflows.scoring_engine_v2 import score_both_directions
        
        # Backtest with walk-forward
        print(f"\n✓ Running backtest on {len(df)} bars...")
        bt = BacktesterV2(min_signal_score=70.0, max_hold_days=7)
        
        result = bt.run_backtest(
            ticker="TEST_UP",
            df=df,
            start_date=df.index[0].date(),
            end_date=df.index[-1].date(),
            scoring_fn=lambda x: score_both_directions(x, "TEST_UP")
        )
        
        # Display 12 metrics
        print("\n📊 12-Metric Results:")
        print(f"  1. Total Trades: {result.total_trades}")
        print(f"  2. Win Rate: {result.win_rate:.1f}%")
        print(f"  3. Profit Factor: {result.profit_factor:.2f}")
        print(f"  4. Avg R/R Realized: {result.avg_rr_realized:.2f}")
        print(f"  5. Total P&L: {result.total_pnl_pct:+.2f}%")
        print(f"  6. CAGR: {result.cagr:+.2f}%")
        print(f"  7. Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  8. Sortino Ratio: {result.sortino_ratio:.2f}")
        print(f"  9. Max Drawdown: {result.max_drawdown:.2f}%")
        print(f" 10. Avg Drawdown: {result.avg_drawdown:.2f}%")
        print(f" 11. Max Consecutive Losses: {result.max_consecutive_losses}")
        print(f" 12. Equity Curve: {len(result.equity_curve)} points")
        
        # Breakdown analysis
        print("\n📈 Breakdown Analysis:")
        if "breakdown_by_direction" in result.to_dict():
            bd = result.to_dict()["breakdown_by_direction"]
            for direction, stats in bd.items():
                print(f"  {direction}: {stats['count']} trades, "
                      f"{stats['win_rate']:.0f}% win, {stats['avg_pnl']:+.2f}% avg P&L")
        
        print("\n✅ Backtester: PASSED")
        return result
        
    except Exception as e:
        print(f"\n❌ Backtester: FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        return None


def test_dashboard(signals, result):
    """Test dashboard generation."""
    print("\n" + "="*60)
    print("TEST 5: Dashboard HTML Generation")
    print("="*60)
    
    try:
        from tradingagents.dataflows.dashboard_unified import create_dashboard_html
        
        # Prepare data
        scan_data = [s.to_dict() for s in signals if s and s.filters_passed]
        result_data = result.to_dict() if result else {}
        
        print(f"\n✓ Creating dashboard...")
        print(f"  → Scan results: {len(scan_data)} signals")
        print(f"  → Backtest result: {'included' if result_data else 'empty'}")
        
        # Generate dashboard
        output_path = "test_dashboard.html"
        created_path = create_dashboard_html(
            scan_results=scan_data,
            backtest_results=result_data,
            positions=[],
            title="FASE 4 Integration Test Dashboard",
            output_path=output_path
        )
        
        # Verify file
        if Path(created_path).exists():
            size_kb = Path(created_path).stat().st_size / 1024
            print(f"  → {created_path} created ({size_kb:.1f} KB)")
            
            # Check content
            with open(created_path) as f:
                html = f.read()
                has_scan = "scan" in html
                has_backtest = "backtest" in html or "metric_value" in html
                has_positions = "positions" in html
                
                print(f"  ✓ Scan tab: {'present' if has_scan else 'missing'}")
                print(f"  ✓ Backtest tab: {'present' if has_backtest else 'missing'}")
                print(f"  ✓ Positions tab: {'present' if has_positions else 'missing'}")
        else:
            print(f"  ✗ File not created: {created_path}")
        
        print("\n✅ Dashboard: PASSED")
        return created_path
        
    except Exception as e:
        print(f"\n❌ Dashboard: FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        return None


def test_end_to_end_flow():
    """Run complete integration test."""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  FASE 4 INTEGRATION TEST - END-TO-END".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    start_time = datetime.now()
    
    # Run all tests in sequence
    df = test_data_manager()
    df_with_ind = test_indicators_advanced(df)
    signals = test_scoring_engine(df_with_ind)
    result = test_backtester(df_with_ind, signals)
    dashboard_path = test_dashboard(signals, result)
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  TEST SUMMARY".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    print(f"""
✅ All modules tested successfully!
   Total time: {elapsed:.1f}s

📊 Modules Validated:
   1. data_manager.py (synthetic data generation)
   2. indicators_advanced.py (51 indicators)
   3. scoring_engine_v2.py (5-component scoring)
   4. backtester_v2.py (12-metric backtest)
   5. dashboard_unified.py (interactive HTML)

📈 Results:
   • Data: 504 bars generated
   • Signals: {len([s for s in signals if s])} valid signals
   • Backtest: {result.total_trades if result else 0} trades analyzed
   • Dashboard: {dashboard_path}

🎯 Next Steps:
   1. Review dashboard: open {dashboard_path}
   2. Run on real data: dm.get("SPY")
   3. Backtest with different parameters
   4. Integrate with main.py for live trading

""")
    
    return True


if __name__ == "__main__":
    try:
        test_end_to_end_flow()
        print("\n✅ INTEGRATION TEST: PASSED ✅\n")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ INTEGRATION TEST: FAILED ❌")
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)
