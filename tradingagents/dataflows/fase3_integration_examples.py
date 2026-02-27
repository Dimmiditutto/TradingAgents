"""
FASE 3 Integration Examples
Complete workflows combining backtesting, reports, and alerts

Examples:
A. Daily Workflow - Scan market, score signals, alert on high-confidence setups
B. Backtest Validation - Historical test and report generation
C. Weekly Workflow - Comprehensive screener report with email summary
D. Live Monitoring - Continuous scoring with threshold-based alerts
"""

import os
from datetime import datetime, timedelta
from typing import List

from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.scoring_engine import ScoringEngine, TradeDirection
from tradingagents.dataflows.backtester import Backtester
from tradingagents.dataflows.report_generator import ReportGenerator
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig


# ============================================================================
# EXAMPLE A: Daily Workflow - Scan and Alert
# ============================================================================

def example_a_daily_workflow():
    """
    Daily Workflow: Scan market, score signals, send alerts for strong setups
    
    Use Case: Run this every morning before market open
    - Scans watchlist
    - Scores each symbol using FASE 2 scoring engine
    - Sends alert for signals >= 75/100
    - Generates HTML report for review
    
    Timeline: ~5-10 minutes
    """
    print("\n" + "="*70)
    print("Example A: Daily Workflow")
    print("="*70)
    
    # Step 1: Define watchlist
    watchlist = [
        # Major indices
        "SPY", "QQQ", "IWM", "DIA",
        # Tech leaders
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA",
        # Finance
        "JPM", "BAC", "GS", "V", "MA",
        # Healthcare
        "UNH", "JNJ", "PFE", "ABBV",
        # Energy
        "XOM", "CVX", "COP",
    ]
    
    print(f"\n[1/4] Scanning {len(watchlist)} symbols...")
    
    # Step 2: Initialize components
    mtf = MultiTimeframeLayer()
    scorer = ScoringEngine()
    
    # Step 3: Score all symbols
    signals = []
    
    for symbol in watchlist:
        try:
            # Get MTF data
            mtf_data = mtf.get_multi_timeframe_data(symbol)
            
            # Score both directions
            long_signal = scorer.score_signal(mtf_data, TradeDirection.LONG)
            short_signal = scorer.score_signal(mtf_data, TradeDirection.SHORT)
            
            # Keep signal with higher score
            if long_signal.total_score >= short_signal.total_score:
                signals.append(long_signal)
            else:
                signals.append(short_signal)
                
        except Exception as e:
            print(f"  ⚠️ Error scoring {symbol}: {e}")
    
    print(f"✓ Scored {len(signals)} symbols")
    
    # Step 4: Filter strong signals (>= 75/100)
    strong_signals = [s for s in signals if s.total_score >= 75.0]
    
    print(f"[2/4] Found {len(strong_signals)} strong signals (>= 75/100)")
    
    for signal in strong_signals[:5]:  # Show top 5
        print(f"  • {signal.symbol}: {signal.direction.name} @ {signal.total_score:.1f}/100")
    
    # Step 5: Generate HTML report
    print(f"\n[3/4] Generating screener report...")
    
    generator = ReportGenerator()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"reports/daily_screener_{timestamp}.html"
    
    os.makedirs("reports", exist_ok=True)
    
    generator.generate_screener_report(
        symbols=[s.symbol for s in signals],
        output_path=report_path,
        title="Daily Market Screener",
        min_score=50.0  # Include all decent signals in report
    )
    
    print(f"✓ Report saved: {report_path}")
    
    # Step 6: Send alerts for strong signals
    print(f"\n[4/4] Sending alerts...")
    
    alert_config = AlertConfig()
    alert_system = AlertSystem(alert_config)
    
    if alert_config.is_discord_enabled() or alert_config.is_email_enabled():
        alert_system.send_batch_alerts(
            signals=strong_signals,
            min_score=75.0
        )
        print(f"✓ Alerts sent for {len(strong_signals)} signals")
    else:
        print("⚠️ No alert channels configured (set DISCORD_WEBHOOK_URL or EMAIL_* vars)")
    
    print("\n✅ Daily workflow complete!")
    print(f"   • Scanned: {len(watchlist)} symbols")
    print(f"   • Strong signals: {len(strong_signals)}")
    print(f"   • Report: {report_path}")
    
    return strong_signals


# ============================================================================
# EXAMPLE B: Backtest Validation
# ============================================================================

def example_b_backtest_validation(symbols: List[str] = None):
    """
    Backtest Validation: Test signal strategy historically
    
    Use Case: Validate your scoring system before going live
    - Runs backtest on historical data
    - Calculates performance metrics
    - Generates detailed HTML report
    
    Timeline: ~2-5 minutes per symbol
    """
    print("\n" + "="*70)
    print("Example B: Backtest Validation")
    print("="*70)
    
    if symbols is None:
        symbols = ["SPY", "QQQ", "IWM"]  # Test on indices
    
    print(f"\n[1/3] Running backtest on {len(symbols)} symbols...")
    
    # Step 1: Initialize backtester
    backtester = Backtester(
        min_signal_score=70.0,  # Only trade signals >= 70/100
        risk_per_trade=2.0,      # Risk 2% per trade
        rr_ratio=2.0,            # Target 2:1 R:R
        max_bars_held=20,        # Force exit after 20 days
        use_trailing_stop=False
    )
    
    # Step 2: Run backtests
    results = []
    
    # Use last 6 months for testing
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    for symbol in symbols:
        print(f"\n  Testing {symbol}...")
        
        try:
            result = backtester.run_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            
            results.append(result)
            
            print(f"    ✓ {result.total_trades} trades, {result.win_rate:.1f}% WR, ${result.total_pnl:.2f} P&L")
            
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
    
    print(f"\n[2/3] Backtest complete - {len(results)} results")
    
    # Step 3: Generate reports
    print(f"\n[3/3] Generating backtest reports...")
    
    generator = ReportGenerator()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    os.makedirs("reports/backtests", exist_ok=True)
    
    for result in results:
        report_path = f"reports/backtests/{result.symbol}_backtest_{timestamp}.html"
        
        generator.generate_backtest_report(
            result=result,
            output_path=report_path
        )
        
        print(f"  ✓ {result.symbol}: {report_path}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("📊 Backtest Summary")
    print("="*70)
    
    total_trades = sum(r.total_trades for r in results)
    avg_win_rate = sum(r.win_rate for r in results) / len(results) if results else 0
    total_pnl = sum(r.total_pnl for r in results)
    
    print(f"\nTotal Trades: {total_trades}")
    print(f"Average Win Rate: {avg_win_rate:.1f}%")
    print(f"Total P&L: ${total_pnl:.2f}")
    
    for result in results:
        print(f"\n{result.symbol}:")
        print(f"  Trades: {result.total_trades}")
        print(f"  Win Rate: {result.win_rate:.1f}%")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown:.1f}%")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    
    print("\n✅ Backtest validation complete!")
    
    return results


# ============================================================================
# EXAMPLE C: Weekly Workflow
# ============================================================================

def example_c_weekly_workflow():
    """
    Weekly Workflow: Comprehensive screener with email summary
    
    Use Case: Run every Sunday evening for week ahead planning
    - Scans expanded watchlist (50+ symbols)
    - Generates detailed HTML report
    - Emails summary to distribution list
    
    Timeline: ~15-20 minutes
    """
    print("\n" + "="*70)
    print("Example C: Weekly Workflow")
    print("="*70)
    
    # Step 1: Expanded watchlist
    watchlist = [
        # Indices
        "SPY", "QQQ", "IWM", "DIA",
        # Tech
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "CRM", "ADBE", "INTC", "AMD",
        # Finance
        "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "BLK",
        # Healthcare
        "UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "ABT", "LLY",
        # Consumer
        "WMT", "HD", "NKE", "MCD", "SBUX", "TGT", "COST",
        # Energy
        "XOM", "CVX", "COP", "SLB", "EOG",
        # Industrials
        "CAT", "BA", "GE", "HON", "UPS", "LMT",
    ]
    
    print(f"\n[1/4] Scanning {len(watchlist)} symbols for weekly outlook...")
    
    # Step 2: Score all
    mtf = MultiTimeframeLayer()
    scorer = ScoringEngine()
    
    signals = []
    
    for i, symbol in enumerate(watchlist, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(watchlist)}")
        
        try:
            mtf_data = mtf.get_multi_timeframe_data(symbol)
            
            long_signal = scorer.score_signal(mtf_data, TradeDirection.LONG)
            short_signal = scorer.score_signal(mtf_data, TradeDirection.SHORT)
            
            if long_signal.total_score >= short_signal.total_score:
                signals.append(long_signal)
            else:
                signals.append(short_signal)
                
        except Exception as e:
            pass  # Skip errors
    
    print(f"✓ Scored {len(signals)} symbols")
    
    # Step 3: Sort by score
    signals.sort(key=lambda s: s.total_score, reverse=True)
    
    top_10 = signals[:10]
    strong_signals = [s for s in signals if s.total_score >= 70.0]
    
    print(f"\n[2/4] Analysis complete:")
    print(f"  • Top 10 signals: {[s.symbol for s in top_10]}")
    print(f"  • Strong setups (>= 70): {len(strong_signals)}")
    
    # Step 4: Generate comprehensive report
    print(f"\n[3/4] Generating weekly report...")
    
    generator = ReportGenerator()
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = f"reports/weekly_outlook_{timestamp}.html"
    
    os.makedirs("reports", exist_ok=True)
    
    generator.generate_screener_report(
        symbols=[s.symbol for s in signals],
        output_path=report_path,
        title=f"Weekly Market Outlook - {datetime.now().strftime('%B %d, %Y')}",
        min_score=50.0
    )
    
    print(f"✓ Report saved: {report_path}")
    
    # Step 5: Email summary
    print(f"\n[4/4] Sending weekly summary email...")
    
    alert_config = AlertConfig()
    alert_system = AlertSystem(alert_config)
    
    if alert_config.is_email_enabled():
        alert_system.send_daily_summary(
            signals=strong_signals,
            report_path=report_path
        )
        print(f"✓ Email sent with report attachment")
    else:
        print("⚠️ Email not configured (set EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO)")
    
    print("\n✅ Weekly workflow complete!")
    print(f"   • Total scanned: {len(watchlist)}")
    print(f"   • Strong setups: {len(strong_signals)}")
    print(f"   • Report: {report_path}")
    
    return signals


# ============================================================================
# EXAMPLE D: Live Monitoring
# ============================================================================

def example_d_live_monitoring(watchlist: List[str] = None, check_interval_minutes: int = 60):
    """
    Live Monitoring: Continuous scoring with threshold alerts
    
    Use Case: Run during market hours for real-time signal detection
    - Rescans watchlist every N minutes
    - Detects new signals crossing threshold
    - Sends immediate alerts
    - Rate limiting prevents spam
    
    Timeline: Continuous (run in background)
    
    Args:
        watchlist: Symbols to monitor (default: major indices + tech)
        check_interval_minutes: Minutes between scans (default: 60)
    """
    print("\n" + "="*70)
    print("Example D: Live Monitoring")
    print("="*70)
    
    if watchlist is None:
        watchlist = [
            "SPY", "QQQ", "IWM",
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA",
            "JPM", "BAC", "XOM"
        ]
    
    print(f"\n📡 Monitoring {len(watchlist)} symbols")
    print(f"   Check interval: {check_interval_minutes} minutes")
    print(f"   Alert threshold: >= 75/100")
    
    # Initialize
    mtf = MultiTimeframeLayer()
    scorer = ScoringEngine()
    alert_config = AlertConfig()
    alert_system = AlertSystem(alert_config)
    
    # Track previous scores to detect changes
    previous_scores = {}
    
    print("\n[Demo Mode] Running single scan...")
    print("   (In production, this would loop continuously)\n")
    
    # In production, this would be: while True:
    scan_time = datetime.now()
    print(f"🔍 Scan at {scan_time.strftime('%H:%M:%S')}")
    
    new_signals = []
    
    for symbol in watchlist:
        try:
            # Get current data
            mtf_data = mtf.get_multi_timeframe_data(symbol)
            
            # Score both directions
            long_signal = scorer.score_signal(mtf_data, TradeDirection.LONG)
            short_signal = scorer.score_signal(mtf_data, TradeDirection.SHORT)
            
            # Pick stronger direction
            signal = long_signal if long_signal.total_score >= short_signal.total_score else short_signal
            
            # Check if this is a new strong signal
            prev_score = previous_scores.get(f"{symbol}_{signal.direction.name}", 0)
            current_score = signal.total_score
            
            # Alert if:
            # 1. Score >= 75 AND
            # 2. Previous score < 75 (new signal crossing threshold)
            if current_score >= 75.0 and prev_score < 75.0:
                new_signals.append(signal)
                
                print(f"  🚨 NEW SIGNAL: {symbol} {signal.direction.name} @ {current_score:.1f}/100")
                
                # Send immediate alert
                if alert_config.is_discord_enabled() or alert_config.is_email_enabled():
                    alert_system.send_signal_alert(
                        signal=signal,
                        alert_reason="New signal crossed threshold during live monitoring"
                    )
            
            elif current_score >= 75.0:
                print(f"  ✓ {symbol}: {signal.direction.name} @ {current_score:.1f}/100 (already tracking)")
            
            # Update tracking
            previous_scores[f"{symbol}_{signal.direction.name}"] = current_score
            
        except Exception as e:
            print(f"  ⚠️ Error scanning {symbol}: {e}")
    
    print(f"\n✓ Scan complete")
    print(f"   • New strong signals: {len(new_signals)}")
    print(f"   • Next scan in {check_interval_minutes} minutes")
    
    if new_signals:
        print(f"\n📢 Alerts sent:")
        for signal in new_signals:
            print(f"   • {signal.symbol} {signal.direction.name} @ {signal.total_score:.1f}/100")
    
    print("\n⚠️ Note: In production, add this to a loop:")
    print("   while True:")
    print("       # ... scan logic ...")
    print(f"       time.sleep({check_interval_minutes * 60})  # Wait {check_interval_minutes} min")
    
    print("\n✅ Live monitoring demo complete!")
    
    return new_signals


# ============================================================================
# Main Runner
# ============================================================================

def main():
    """
    Run all integration examples
    
    Uncomment the examples you want to test
    """
    print("\n" + "="*70)
    print("🚀 FASE 3 INTEGRATION EXAMPLES")
    print("="*70)
    
    print("\nAvailable workflows:")
    print("  A. Daily Workflow - Morning scan and alerts")
    print("  B. Backtest Validation - Historical testing")
    print("  C. Weekly Workflow - Comprehensive weekend analysis")
    print("  D. Live Monitoring - Intraday signal detection")
    
    print("\n" + "-"*70)
    
    # Example A: Daily workflow
    print("\nRunning Example A: Daily Workflow...")
    try:
        signals_a = example_a_daily_workflow()
    except Exception as e:
        print(f"❌ Example A error: {e}")
        import traceback
        traceback.print_exc()
    
    # Example B: Backtest validation
    # Uncomment to run:
    # print("\nRunning Example B: Backtest Validation...")
    # try:
    #     results_b = example_b_backtest_validation(["SPY", "QQQ"])
    # except Exception as e:
    #     print(f"❌ Example B error: {e}")
    
    # Example C: Weekly workflow
    # Uncomment to run:
    # print("\nRunning Example C: Weekly Workflow...")
    # try:
    #     signals_c = example_c_weekly_workflow()
    # except Exception as e:
    #     print(f"❌ Example C error: {e}")
    
    # Example D: Live monitoring
    # Uncomment to run:
    # print("\nRunning Example D: Live Monitoring...")
    # try:
    #     signals_d = example_d_live_monitoring()
    # except Exception as e:
    #     print(f"❌ Example D error: {e}")
    
    print("\n" + "="*70)
    print("✅ Integration examples complete!")
    print("="*70)
    
    print("\n📝 Quick Start:")
    print("   1. Configure alerts: Set DISCORD_WEBHOOK_URL and/or EMAIL_* variables")
    print("   2. Run daily workflow: python -c 'from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()'")
    print("   3. Review reports in: reports/")
    print("   4. Check alert history: alert_system.get_alert_history()")


if __name__ == "__main__":
    main()
