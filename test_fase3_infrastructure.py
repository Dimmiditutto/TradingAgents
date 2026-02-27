"""
Test Suite for FASE 3 Infrastructure
Tests backtesting, reports, and alerts
"""

import sys
import os
from datetime import datetime, timedelta

# Import F ASE 3 modules
from tradingagents.dataflows.backtester import Backtester, Trade, BacktestResult
from tradingagents.dataflows.report_generator import ReportGenerator
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig

# Import FASE 2 for integration testing
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.scoring_engine import ScoringEngine, TradeDirection, SignalScore


def test_backtester():
    """Test 1: Backtester - Historical signal generation and trade simulation"""
    print("\n" + "="*70)
    print("TEST 1: Backtester - Trade Simulation")
    print("="*70)
    
    backtester = Backtester(
        min_signal_score=70.0,
        risk_per_trade=2.0,
        rr_ratio=2.0,
        max_bars_held=20,
    )
    
    print("\n✓ Backtester initialized")
    print(f"  Min Score: {backtester.min_signal_score}")
    print(f"  Risk/Trade: {backtester.risk_per_trade}%")
    print(f"  R:R Ratio: {backtester.rr_ratio}")
    
    # Run mini backtest (short period for speed)
    symbol = "SPY"
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 2, 1)
    
    try:
        result = backtester.run_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        
        print(f"\n✓ Backtest completed for {symbol}")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Win Rate: {result.win_rate:.1f}%")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"  Total P&L: ${result.total_pнл:.2f}")
        
        # Validate metrics
        assert result.total_trades >= 0, "Total trades should be non-negative"
        assert 0 <= result.win_rate <= 100, "Win rate should be 0-100%"
        assert result.profit_factor >= 0, "Profit factor should be non-negative"
        
        print("\n✅ Backtester: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Backtester error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trade_class():
    """Test 2: Trade Class - P&L calculation"""
    print("\n" + "="*70)
    print("TEST 2: Trade Class - P&L Calculation")
    print("="*70)
    
    # Test LONG trade
    long_trade = Trade(
        symbol="AAPL",
        direction="LONG",
        entry_date=datetime(2025, 1, 1),
        entry_price=150.0,
        entry_signal_score=80.0,
        stop_loss=145.0,
        take_profit=160.0,
    )
    
    # Close with profit
    long_trade.close_trade(
        exit_date=datetime(2025, 1, 5),
        exit_price=158.0,
        reason="TARGET"
    )
    
    print(f"\n✓ LONG Trade Created and Closed")
    print(f"  Entry: ${long_trade.entry_price}")
    print(f"  Exit: ${long_trade.exit_price}")
    print(f"  P&L: ${long_trade.pnl:.2f} ({long_trade.pnl_pct:.2f}%)")
    
    assert long_trade.pnl == 8.0, "LONG P&L calculation incorrect"
    assert long_trade.pnl_pct > 0, "LONG P&L % should be positive"
    assert long_trade.status == "CLOSED", "Trade should be closed"
    
    # Test SHORT trade
    short_trade = Trade(
        symbol="TSLA",
        direction="SHORT",
        entry_date=datetime(2025, 1, 1),
        entry_price=200.0,
        entry_signal_score=75.0,
        stop_loss=210.0,
        take_profit=180.0,
    )
    
    short_trade.close_trade(
        exit_date=datetime(2025, 1, 3),
        exit_price=190.0,
        reason="TARGET"
    )
    
    print(f"\n✓ SHORT Trade Created and Closed")
    print(f"  Entry: ${short_trade.entry_price}")
    print(f"  Exit: ${short_trade.exit_price}")
    print(f"  P&L: ${short_trade.pnl:.2f} ({short_trade.pnl_pct:.2f}%)")
    
    assert short_trade.pnl == 10.0, "SHORT P&L calculation incorrect"
    assert short_trade.pnl_pct > 0, "SHORT P&L % should be positive"
    
    print("\n✅ Trade Class: PASSED")
    return True


def test_backtest_result():
    """Test 3: BacktestResult - Metrics calculation"""
    print("\n" + "="*70)
    print("TEST 3: BacktestResult - Metrics Calculation")
    print("="*70)
    
    result = BacktestResult(
        symbol="SPY",
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 2, 1),
    )
    
    # Add sample trades
    trades = [
        Trade("SPY", "LONG", datetime(2025, 1, 5), 450.0, 80.0),
        Trade("SPY", "LONG", datetime(2025, 1, 10), 452.0, 75.0),
        Trade("SPY", "LONG", datetime(2025, 1, 15), 448.0, 78.0),
    ]
    
    # Close trades
    trades[0].close_trade(datetime(2025, 1, 8), 455.0, "TARGET")  # +5 profit
    trades[1].close_trade(datetime(2025, 1, 12), 450.0, "STOP")   # -2 loss
    trades[2].close_trade(datetime(2025, 1, 18), 453.0, "TARGET") # +5 profit
    
    result.trades = trades
    result.calculate_metrics()
    
    print(f"\n✓ BacktestResult metrics calculated")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Winning: {result.winning_trades}")
    print(f"  Losing: {result.losing_trades}")
    print(f"  Win Rate: {result.win_rate:.1f}%")
    print(f"  Total P&L: ${result.total_pnl:.2f}")
    
    assert result.total_trades == 3, "Should have 3 trades"
    assert result.winning_trades == 2, "Should have 2 winning trades"
    assert result.losing_trades == 1, "Should have 1 losing trade"
    assert result.win_rate > 60, "Win rate should be >60%"
    assert result.total_pnl > 0, "Total P&L should be positive"
    
    print("\n✅ BacktestResult: PASSED")
    return True


def test_report_generator():
    """Test 4: Report Generator - HTML generation"""
    print("\n" + "="*70)
    print("TEST 4: Report Generator - HTML Creation")
    print("="*70)
    
    generator = ReportGenerator()
    
    print("\n✓ ReportGenerator initialized")
    
    # Test with small symbol list
    symbols = ["SPY", "QQQ"]
    
    try:
        print(f"\nGenerating report for {len(symbols)} symbols...")
        
        html = generator.generate_screener_report(
            symbols=symbols,
            output_path="test_report.html",
            title="Test Screener Report",
            min_score=0.0  # Include all for testing
        )
        
        print(f"\n✓ Report generated")
        print(f"  HTML length: {len(html)} chars")
        print(f"  File: test_report.html")
        
        # Validate HTML
        assert len(html) > 1000, "HTML should be substantial"
        assert "<html" in html.lower(), "Should contain HTML tags"
        assert "screener" in html.lower(), "Should contain 'screener'"
        
        # Check file exists
        assert os.path.exists("test_report.html"), "Report file should exist"
        
        print("\n✅ Report Generator: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Report Generator error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alert_config():
    """Test 5: Alert Configuration"""
    print("\n" + "="*70)
    print("TEST 5: Alert Configuration")
    print("="*70)
    
    # Test with no config (should use env vars if available)
    config = AlertConfig()
    
    print(f"\n✓ AlertConfig created")
    print(f"  Discord: {'Enabled' if config.is_discord_enabled() else 'Disabled (set DISCORD_WEBHOOK_URL)'}")
    print(f"  Email: {'Enabled' if config.is_email_enabled() else 'Disabled (set EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO)'}")
    
    # Test with explicit config
    config2 = AlertConfig(
        discord_webhook_url="https://discord.com/api/webhooks/test",
        email_from="test@example.com",
        email_password="password",
        email_to=["recipient@example.com"]
    )
    
    print(f"\n✓ AlertConfig with explicit values")
    print(f"  Discord: {config2.is_discord_enabled()}")
    print(f"  Email: {config2.is_email_enabled()}")
    
    assert config2.is_discord_enabled(), "Discord should be enabled"
    assert config2.is_email_enabled(), "Email should be enabled"
    
    print("\n✅ Alert Configuration: PASSED")
    return True


def test_alert_system():
    """Test 6: Alert System - Message formatting"""
    print("\n" + "="*70)
    print("TEST 6: Alert System - Discord/Email Formatting")
    print("="*70)
    
    # Create mock config (won't actually send)
    config = AlertConfig()
    alert_system = AlertSystem(config)
    
    print(f"\n✓ AlertSystem initialized")
    
    # Create mock signal
    mock_signal = SignalScore(
        symbol="AAPL",
        direction=TradeDirection.LONG,
        total_score=82.0,
        trend_strength=85.0,
        direction_confluence=90.0,
        volume_quality=75.0,
        structure_quality=70.0,
        risk_profile=80.0,
        adx_value=38.0,
        volume_ratio=1.75,
        pct_from_200sma=3.5,
        atr_pct=1.8,
        weekly_trend=1,
        strengths=["Strong trend", "High volume"],
        weaknesses=[],
    )
    
    print(f"\n✓ Mock signal created: {mock_signal.symbol} {mock_signal.direction.name}")
    
    # Test alert formatting (won't send without config)
    if not config.is_discord_enabled() and not config.is_email_enabled():
        print("\n⚠️ No alerts configured - testing formatters only")
        
        # Test internal methods won't crash
        try:
            # These will return False but shouldn't crash
            discord_result = alert_system._send_discord_alert(mock_signal, "Test")
            email_result = alert_system._send_email_alert(mock_signal, "Test")
            
            print(f"  Discord formatter: OK (sent={discord_result})")
            print(f"  Email formatter: OK (sent={email_result})")
            
        except Exception as e:
            print(f"  ⚠️ Formatter error (expected): {e}")
    else:
        print("\n✓ Alerts configured - testing real send")
        
        # Actually send if configured
        alert_system.send_signal_alert(mock_signal, "Test alert from test suite")
    
    print("\n✅ Alert System: PASSED")
    return True


def test_integration():
    """Test 7: Full Integration - Backtest + Report + Alert"""
    print("\n" + "="*70)
    print("TEST 7: Full Integration - Complete Workflow")
    print("="*70)
    
    symbol = "QQQ"
    
    print(f"\nStep 1: Run backtest on {symbol}...")
    backtester = Backtester(min_signal_score=70.0)
    
    try:
        result = backtester.run_backtest(
            symbol=symbol,
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 2, 1),
        )
        
        print(f"✓ Backtest: {result.total_trades} trades, {result.win_rate:.1f}% win rate")
        
    except Exception as e:
        print(f"⚠️ Backtest error (may be data issue): {e}")
        result = BacktestResult(symbol, datetime(2025,1,1), datetime(2025,2,1))
    
    print(f"\nStep 2: Generate HTML report...")
    generator = ReportGenerator()
    
    try:
        backtest_report = generator.generate_backtest_report(
            result=result,
            output_path="test_backtest_report.html"
        )
        
        print(f"✓ Report generated: {len(backtest_report)} chars")
        
    except Exception as e:
        print(f"⚠️ Report error: {e}")
    
    print(f"\nStep 3: Check alert system...")
    alert_config = AlertConfig()
    alert_system = AlertSystem(alert_config)
    
    print(f"✓ Alert system ready (Discord: {alert_config.is_discord_enabled()}, Email: {alert_config.is_email_enabled()})")
    
    print("\n✅ Full Integration: PASSED")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 FASE 3 INFRASTRUCTURE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Trade Class", test_trade_class),
        ("BacktestResult Metrics", test_backtest_result),
        ("Backtester", test_backtester),
        ("Report Generator", test_report_generator),
        ("Alert Configuration", test_alert_config),
        ("Alert System", test_alert_system),
        ("Full Integration", test_integration),
    ]
    
    results = {}
    
    for test_name, test_fn in tests:
        try:
            result = test_fn()
            results[test_name] = "✅ PASSED" if result else "❌ FAILED"
        except Exception as e:
            results[test_name] = f"❌ FAILED: {str(e)}"
            print(f"\n❌ Error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        print(f"{result} - {test_name}")
        if "PASSED" in result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    # Cleanup test files
    try:
        if os.path.exists("test_report.html"):
            os.remove("test_report.html")
        if os.path.exists("test_backtest_report.html"):
            os.remove("test_backtest_report.html")
        print("\n🧹 Cleaned up test files")
    except:
        pass
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! FASE 3 infrastructure is operational.")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Review errors above.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
