# FASE 3 Deployment Checklist

Production readiness checklist for deploying TradingAgents with backtesting, reports, and alerts.

---

## Pre-Deployment

### 1. Environment Setup

- [ ] **Python Dependencies Installed**
  ```bash
  pip install requests plotly pandas numpy yfinance alpha_vantage
  ```

- [ ] **Data Source Configuration**
  - [ ] Alpha Vantage API key set: `export ALPHA_VANTAGE_API_KEY="..."`
  - [ ] yfinance tested: `python -c "import yfinance; print(yfinance.download('SPY', period='1d'))"`

- [ ] **Alert Channels Configured**
  - [ ] Discord webhook URL: `export DISCORD_WEBHOOK_URL="..."`
  - [ ] Email credentials:
    ```bash
    export EMAIL_FROM="your@email.com"
    export EMAIL_PASSWORD="app_password"
    export EMAIL_TO="recipient@example.com"
    ```
  - [ ] Test alerts sent successfully

- [ ] **Directories Created**
  ```bash
  mkdir -p reports
  mkdir -p reports/backtests
  mkdir -p reports/daily
  mkdir -p reports/weekly
  ```

### 2. Testing

- [ ] **Run Test Suite**
  ```bash
  python test_fase3_infrastructure.py
  ```
  All 7 tests should pass ✅

- [ ] **Test Individual Components**
  
  **Backtesting**:
  ```python
  from tradingagents.dataflows.backtester import Backtester
  from datetime import datetime
  
  backtester = Backtester()
  result = backtester.run_backtest("SPY", datetime(2024, 8, 1), datetime(2025, 2, 1))
  print(f"Trades: {result.total_trades}, Win Rate: {result.win_rate:.1f}%")
  ```
  - [ ] Backtest completes without errors
  - [ ] Results are reasonable (not 100% win rate or extreme P&L)
  
  **Report Generation**:
  ```python
  from tradingagents.dataflows.report_generator import ReportGenerator
  
  generator = ReportGenerator()
  generator.generate_screener_report(["SPY", "QQQ"], "test_report.html", "Test")
  ```
  - [ ] Report generated successfully
  - [ ] HTML opens in browser
  - [ ] Charts display correctly
  
  **Alerts**:
  ```python
  from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig
  from tradingagents.dataflows.scoring_engine import SignalScore, TradeDirection
  
  alert_system = AlertSystem(AlertConfig())
  test_signal = SignalScore(
      symbol="TEST", direction=TradeDirection.LONG, total_score=85.0,
      trend_strength=90.0, direction_confluence=85.0, volume_quality=80.0,
      structure_quality=85.0, risk_profile=85.0, adx_value=35.0,
      volume_ratio=1.5, pct_from_200sma=2.5, atr_pct=1.8, weekly_trend=1,
      strengths=["Test"], weaknesses=[]
  )
  alert_system.send_signal_alert(test_signal, "Test alert")
  ```
  - [ ] Discord alert received (if configured)
  - [ ] Email alert received (if configured)

### 3. Backtest Validation

- [ ] **Historical Validation Complete**
  
  Test on major indices:
  ```python
  from tradingagents.dataflows.fase3_integration_examples import example_b_backtest_validation
  
  results = example_b_backtest_validation(["SPY", "QQQ", "IWM"])
  ```
  
  For each symbol, verify:
  - [ ] Total trades > 10 (sufficient sample size)
  - [ ] Win rate 40-70% (realistic range)
  - [ ] Profit factor > 1.0 (profitable overall)
  - [ ] Max drawdown < 30% (acceptable risk)
  - [ ] Sharpe ratio > 0.5 (risk-adjusted returns acceptable)

- [ ] **Parameter Tuning** (if results poor)
  
  Adjust backtester parameters:
  ```python
  backtester = Backtester(
      min_signal_score=65.0,  # Lower if too few trades
      risk_per_trade=1.5,     # Lower if drawdown too high
      rr_ratio=2.5,           # Increase if profit factor low
      max_bars_held=15        # Decrease if trades hold too long
  )
  ```
  
  - [ ] Re-run backtests with new parameters
  - [ ] Document final parameters used

### 4. Configuration Review

- [ ] **Watchlist Defined**
  
  Create your watchlist file:
  ```python
  # watchlist.py
  DAILY_WATCHLIST = [
      # Indices
      "SPY", "QQQ", "IWM", "DIA",
      # Tech
      "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA",
      # Finance
      "JPM", "BAC", "GS", "V", "MA",
      # Add your symbols...
  ]
  
  WEEKLY_WATCHLIST = DAILY_WATCHLIST + [
      # Extended list for weekend deep dive
      "NFLX", "META", "CRM", "ADBE", "INTC", "AMD",
      # Add more...
  ]
  ```
  
  - [ ] Daily watchlist: 20-30 symbols (fast scan)
  - [ ] Weekly watchlist: 50-100 symbols (comprehensive)

- [ ] **Thresholds Set**
  
  ```python
  # config.py
  MIN_SIGNAL_SCORE = 70.0        # Minimum score to trade
  ALERT_THRESHOLD = 75.0         # Minimum score to alert
  REPORT_MIN_SCORE = 50.0        # Minimum score to include in report
  
  BACKTEST_PARAMS = {
      "min_signal_score": 70.0,
      "risk_per_trade": 2.0,
      "rr_ratio": 2.0,
      "max_bars_held": 20
  }
  ```
  
  - [ ] Thresholds match your risk tolerance
  - [ ] Backtest parameters documented

---

## Deployment

### 1. Scheduled Tasks Setup

**Daily Morning Scan** (8:00 AM ET, weekdays):

- [ ] **Create Script**: `scripts/daily_scan.py`
  ```python
  from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow
  import logging
  
  logging.basicConfig(
      filename='logs/daily_scan.log',
      level=logging.INFO,
      format='%(asctime)s - %(levelname)s - %(message)s'
  )
  
  try:
      logging.info("Starting daily scan...")
      signals = example_a_daily_workflow()
      logging.info(f"Daily scan complete: {len(signals)} signals")
  except Exception as e:
      logging.error(f"Daily scan failed: {e}", exc_info=True)
  ```

- [ ] **Schedule Task**
  
  **Linux/Mac (cron)**:
  ```bash
  crontab -e
  
  # Daily scan at 8:00 AM ET (weekdays)
  0 8 * * 1-5 cd /path/to/TradingAgents && /path/to/python scripts/daily_scan.py
  ```
  
  **Windows (Task Scheduler)**:
  - Open Task Scheduler
  - Create Task: "TradingAgents Daily Scan"
  - Trigger: Daily at 8:00 AM, weekdays only
  - Action: `python C:\path\to\TradingAgents\scripts\daily_scan.py`
  - Start in: `C:\path\to\TradingAgents`

- [ ] **Test Schedule**
  - [ ] Manually run script: `python scripts/daily_scan.py`
  - [ ] Check logs: `tail -f logs/daily_scan.log`
  - [ ] Verify report generated: `ls reports/`
  - [ ] Confirm alerts received

**Weekly Report** (Sunday 8:00 PM ET):

- [ ] **Create Script**: `scripts/weekly_report.py`
  ```python
  from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow
  import logging
  
  logging.basicConfig(
      filename='logs/weekly_report.log',
      level=logging.INFO,
      format='%(asctime)s - %(levelname)s - %(message)s'
  )
  
  try:
      logging.info("Starting weekly workflow...")
      signals = example_c_weekly_workflow()
      logging.info(f"Weekly workflow complete: {len(signals)} signals")
  except Exception as e:
      logging.error(f"Weekly workflow failed: {e}", exc_info=True)
  ```

- [ ] **Schedule Task**
  
  **Linux/Mac (cron)**:
  ```bash
  # Weekly report at 8:00 PM ET (Sunday)
  0 20 * * 0 cd /path/to/TradingAgents && /path/to/python scripts/weekly_report.py
  ```
  
  **Windows (Task Scheduler)**:
  - Create Task: "TradingAgents Weekly Report"
  - Trigger: Weekly on Sunday at 8:00 PM
  - Action: `python C:\path\to\TradingAgents\scripts\weekly_report.py`

### 2. Monitoring Setup

- [ ] **Logging Configured**
  ```bash
  mkdir -p logs
  touch logs/daily_scan.log
  touch logs/weekly_report.log
  touch logs/alerts.log
  ```

- [ ] **Log Rotation Setup**
  
  **Linux (logrotate)**:
  ```bash
  # /etc/logrotate.d/tradingagents
  /path/to/TradingAgents/logs/*.log {
      daily
      rotate 30
      compress
      missingok
      notifempty
  }
  ```
  
  **Windows**: Use Windows Task Scheduler to run cleanup script weekly

- [ ] **Health Check Script**
  ```python
  # scripts/health_check.py
  import os
  from datetime import datetime, timedelta
  
  # Check if daily scan ran today
  report_files = os.listdir("reports")
  today = datetime.now().strftime("%Y%m%d")
  today_reports = [f for f in report_files if today in f]
  
  if not today_reports:
      print("⚠️ WARNING: No reports generated today")
      # Send alert to yourself
  else:
      print(f"✅ OK: {len(today_reports)} reports generated today")
  
  # Check log for errors
  with open("logs/daily_scan.log") as f:
      recent_logs = f.readlines()[-100:]  # Last 100 lines
      errors = [line for line in recent_logs if "ERROR" in line]
      
      if errors:
          print(f"⚠️ WARNING: {len(errors)} errors in recent logs")
          for error in errors[-5:]:  # Show last 5
              print(error.strip())
  ```
  
  - [ ] Health check runs daily (9:00 AM)
  - [ ] Alerts you if something fails

### 3. Alert Delivery Verification

- [ ] **Discord Channel Setup**
  - [ ] Create dedicated channel: `#trading-alerts`
  - [ ] Webhook configured to post to this channel
  - [ ] Test message received
  - [ ] Notifications enabled on mobile

- [ ] **Email Delivery**
  - [ ] Test email received in inbox (not spam)
  - [ ] HTML formatting displays correctly
  - [ ] Links work
  - [ ] Attachment opens (if included)

- [ ] **Rate Limiting Working**
  - [ ] Send 2 alerts for same symbol within 1 hour
  - [ ] Verify 2nd alert blocked
  - [ ] Check logs confirm rate limiting

---

## Post-Deployment

### 1. First Week Monitoring

- [ ] **Day 1**: Check all scheduled tasks ran
  ```bash
  # Check cron ran
  grep CRON /var/log/syslog | grep daily_scan
  
  # Or check Task Scheduler history (Windows)
  ```

- [ ] **Day 2-7**: Monitor alerts
  - [ ] Count alerts received per day
  - [ ] Review signal quality (false positives?)
  - [ ] Adjust `ALERT_THRESHOLD` if too many/few alerts

- [ ] **End of Week 1**: Review reports
  - [ ] Check daily reports generated successfully
  - [ ] Verify weekly report complete
  - [ ] Email delivery working

### 2. Performance Tracking

- [ ] **Create Performance Log**
  ```python
  # Track each alerted signal
  # Date, Symbol, Direction, Score, Actual Outcome (7 days later)
  ```
  
  Example:
  ```
  2025-02-25, SPY, LONG, 82.0, +3.5% (hit target)
  2025-02-25, AAPL, LONG, 78.0, -1.2% (stopped out)
  2025-02-26, QQQ, SHORT, 80.0, +2.8% (hit target)
  ```

- [ ] **Weekly Review Meeting**
  - [ ] Review performance vs backtest expectations
  - [ ] Identify patterns in false signals
  - [ ] Adjust parameters if needed

### 3. Maintenance Tasks

- [ ] **Monthly**
  - [ ] Review log files for errors
  - [ ] Clean up old reports (keep last 90 days)
    ```bash
    find reports -name "*.html" -mtime +90 -delete
    ```
  - [ ] Update watchlist (add/remove symbols)

- [ ] **Quarterly**
  - [ ] Re-run backtests with latest data
  - [ ] Validate strategy still performing
  - [ ] Document any parameter changes

- [ ] **As Needed**
  - [ ] Update dependencies: `pip install --upgrade requests plotly pandas`
  - [ ] Check for breaking changes in APIs (yfinance, Alpha Vantage)

---

## Rollback Plan

If something goes wrong:

### 1. Disable Scheduled Tasks

**Linux/Mac**:
```bash
crontab -e
# Comment out lines with #
```

**Windows**:
- Open Task Scheduler
- Right-click task → Disable

### 2. Stop Alerts

```bash
# Temporarily rename webhook URL
export DISCORD_WEBHOOK_URL=""
export EMAIL_FROM=""
```

### 3. Investigate

- [ ] Check logs: `tail -100 logs/daily_scan.log`
- [ ] Look for errors: `grep ERROR logs/*.log`
- [ ] Test components individually:
  ```python
  # Test backtester
  from tradingagents.dataflows.backtester import Backtester
  backtester = Backtester()
  # ...
  
  # Test report generator
  from tradingagents.dataflows.report_generator import ReportGenerator
  generator = ReportGenerator()
  # ...
  
  # Test alert system
  from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig
  alert_system = AlertSystem(AlertConfig())
  # ...
  ```

### 4. Fix and Re-deploy

- [ ] Fix identified issue
- [ ] Re-run test suite: `python test_fase3_infrastructure.py`
- [ ] Test manually before re-enabling schedule

---

## Success Criteria

After 1 week, you should have:

- [ ] ✅ 5 daily reports generated (Mon-Fri)
- [ ] ✅ 1 weekly report generated (Sunday)
- [ ] ✅ 5-20 alerts sent (depending on market conditions)
- [ ] ✅ No errors in logs (or only minor, handled errors)
- [ ] ✅ All scheduled tasks running on time

After 1 month, you should have:

- [ ] ✅ 20+ daily reports
- [ ] ✅ 4 weekly reports
- [ ] ✅ Performance tracking data collected
- [ ] ✅ Initial validation: Are alerted setups performing as expected?

---

## Troubleshooting Common Issues

### Issue: Scheduled task not running

**Check 1**: Verify cron/Task Scheduler entry
```bash
# Linux/Mac
crontab -l | grep daily_scan

# Windows: Open Task Scheduler and check history
```

**Check 2**: Test script manually
```bash
cd /path/to/TradingAgents
python scripts/daily_scan.py
```

**Check 3**: Check PATH and environment variables
```bash
# cron doesn't inherit your shell environment
# Add to crontab:
PATH=/usr/local/bin:/usr/bin:/bin
ALPHA_VANTAGE_API_KEY=your_key
# ... other vars ...
```

### Issue: No alerts being sent

**Check 1**: Verify thresholds
```python
# Are any signals crossing ALERT_THRESHOLD?
signals = [...]  # From scan
strong_signals = [s for s in signals if s.total_score >= 75.0]
print(f"Strong signals: {len(strong_signals)}")
```

**Check 2**: Check rate limiting
```python
# View alert history
alert_system.get_alert_history(hours=24)
```

**Check 3**: Test alert channels
```python
# Send test alert
alert_system.send_signal_alert(test_signal, "Test")
```

### Issue: Reports not generating

**Check 1**: Check directory permissions
```bash
ls -la reports/
mkdir -p reports/daily reports/weekly
chmod 755 reports
```

**Check 2**: Check disk space
```bash
df -h
```

**Check 3**: Check for data issues
```python
# Test data fetching
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
mtf = MultiTimeframeLayer()
mtf_data = mtf.get_multi_timeframe_data("SPY")
print(f"Weekly: {len(mtf_data.weekly_df)} bars")
print(f"Daily: {len(mtf_data.daily_df)} bars")
```

---

## Contact & Support

- **Documentation**: `docs/FASE3_ARCHITECTURE.md`
- **Quick Reference**: `docs/FASE3_QUICK_REFERENCE.md`
- **Examples**: `tradingagents/dataflows/fase3_integration_examples.py`
- **Test Suite**: `test_fase3_infrastructure.py`

**Before reporting issues**:
1. Run test suite: `python test_fase3_infrastructure.py`
2. Check logs: `tail -100 logs/*.log`
3. Test individual components
4. Review this checklist

---

## Sign-off

Deployment complete when ALL items checked:

- [ ] All pre-deployment tests pass
- [ ] Backtest validation acceptable
- [ ] Scheduled tasks configured and tested
- [ ] Alerts delivered successfully
- [ ] Monitoring and logging in place
- [ ] First week monitoring complete
- [ ] Performance tracking started

**Deployed by**: _______________  
**Date**: _______________  
**Version**: FASE 3 v1.0  

**Notes**:
_______________________________________________________________________
_______________________________________________________________________
_______________________________________________________________________
