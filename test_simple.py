#!/usr/bin/env python3
"""Simple test - run from workspace root"""

import sys
from pathlib import Path

# Ensure proper imports
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("FASE 4 - Simple Integration Test")
print("="*70)

# Test 1: Data Manager
print("\n[1/5] Testing data_manager.py...")
try:
    from tradingagents.dataflows.data_manager import generate_synthetic, get_sp500_subset
    
    df = generate_synthetic("TEST", n_bars=100, trend="up", seed=42)
    print(f"  ✓ Generated {len(df)} bars of synthetic data")
    
    tickers = get_sp500_subset(["technology"])
    print(f"  ✓ Found {len(tickers)} tech tickers: {tickers[:3]}")
    print("  ✅ data_manager.py: OK")
except Exception as e:
    print(f"  ❌ data_manager.py: {e}")
    sys.exit(1)

# Test 2: Indicators
print("\n[2/5] Testing indicators_advanced.py...")
try:
    from tradingagents.dataflows.indicators_advanced import compute_all
    
    df_ind = compute_all(df)
    n_cols = len(df_ind.columns) - len(df.columns)
    print(f"  ✓ Added {n_cols} indicators")
    print(f"  ✓ Sample: RSI={df_ind['RSI'].iloc[-1]:.1f}, ADX={df_ind['ADX'].iloc[-1]:.1f}")
    print("  ✅ indicators_advanced.py: OK")
except Exception as e:
    print(f"  ❌ indicators_advanced.py: {e}")
    sys.exit(1)

# Test 3: Scoring
print("\n[3/5] Testing scoring_engine_v2.py...")
try:
    from tradingagents.dataflows.scoring_engine_v2 import score_both_directions
    
    signals = score_both_directions(df_ind, "TEST")
    valid = [s for s in signals if s]
    print(f"  ✓ Generated {len([s for s in signals if s])} valid signals")
    if valid:
        sig = valid[-1]
        print(f"  ✓ Last signal: {sig.direction} Score={sig.score:.0f}, "
              f"Filters={'✓' if sig.filters_passed else '✗'}")
    print("  ✅ scoring_engine_v2.py: OK")
except Exception as e:
    print(f"  ❌ scoring_engine_v2.py: {e}")
    sys.exit(1)

# Test 4: Backtester
print("\n[4/5] Testing backtester_v2.py...")
try:
    from tradingagents.dataflows.backtester_v2 import BacktesterV2
    
    bt = BacktesterV2(min_signal_score=70.0, max_hold_days=7)
    result = bt.run_backtest(
        ticker="TEST",
        df=df_ind,
        start_date=df_ind.index[0].date(),
        end_date=df_ind.index[-1].date(),
        scoring_fn=lambda x: score_both_directions(x, "TEST")
    )
    
    print(f"  ✓ Backtest: {result.total_trades} trades")
    print(f"  ✓ Win Rate: {result.win_rate:.1f}%")
    print(f"  ✓ Sharpe: {result.sharpe_ratio:.2f}")
    print("  ✅ backtester_v2.py: OK")
except Exception as e:
    print(f"  ❌ backtester_v2.py: {e}")
    sys.exit(1)

# Test 5: Dashboard
print("\n[5/5] Testing dashboard_unified.py...")
try:
    from tradingagents.dataflows.dashboard_unified import create_dashboard_html
    
    scan_data = [s.to_dict() for s in signals if s and s.filters_passed]
    result_data = result.to_dict()
    
    path = create_dashboard_html(
        scan_results=scan_data,
        backtest_results=result_data,
        output_path="test_dashboard.html"
    )
    
    size = Path(path).stat().st_size / 1024
    print(f"  ✓ Dashboard created: {path} ({size:.1f} KB)")
    print("  ✅ dashboard_unified.py: OK")
except Exception as e:
    print(f"  ❌ dashboard_unified.py: {e}")
    sys.exit(1)

# Summary
print("\n" + "="*70)
print("✅ ALL TESTS PASSED - FASE 4 IS READY!")
print("="*70)
print(f"""
📊 Dashboard: test_dashboard.html
   • Indicators: 51+ technical indicators
   • Scoring: 5-component weighted (0-100)
   • Backtest: 12 metrics + breakdown analysis
   • Visualization: Interactive HTML dashboard

🎯 Next steps:
   1. Open test_dashboard.html in browser
   2. Run on real data: dm.get("SPY")
   3. Integrate with main.py
   4. Deploy to production

""")
