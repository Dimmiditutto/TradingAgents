# FASE 3 Quick Reference

Quick start guide for using backtesting, reports, and alerts.

---

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install requests plotly pandas numpy yfinance alpha_vantage
```

### 2. Configure Alerts (Optional)
```bash
# Discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK"

# Email (Gmail example)
export EMAIL_FROM="your@gmail.com"
export EMAIL_PASSWORD="app_specific_password"  # Not regular password!
export EMAIL_TO="recipient@example.com"
```

**Gmail App Password**:
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Generate app password
3. Use that (not your regular password)

### 3. Test Installation
```bash
python test_fase3_infrastructure.py
```

Expected: All tests pass ✅

---

## Common Tasks

### Task 1: Run Daily Scan

**What**: Scan watchlist, generate report, send alerts

```python
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.scoring_engine import ScoringEngine, TradeDirection
from tradingagents.dataflows.report_generator import ReportGenerator
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig

# Define watchlist
watchlist = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL"]

# Score symbols
mtf = MultiTimeframeLayer()
scorer = ScoringEngine()

signals = []
for symbol in watchlist:
    mtf_data = mtf.get_multi_timeframe_data(symbol)
    
    long_signal = scorer.score_signal(mtf_data, TradeDirection.LONG)
    short_signal = scorer.score_signal(mtf_data, TradeDirection.SHORT)
    
    # Keep stronger direction
    if long_signal.total_score >= short_signal.total_score:
        signals.append(long_signal)
    else:
        signals.append(short_signal)

# Generate report
generator = ReportGenerator()
generator.generate_screener_report(
    symbols=watchlist,
    output_path="reports/daily_scan.html",
    title="Daily Market Scan",
    min_score=50.0
)

# Send alerts for strong signals
alert_system = AlertSystem(AlertConfig())
alert_system.send_batch_alerts(signals, min_score=75.0)

print("✅ Daily scan complete! Check reports/daily_scan.html")
```

**Run**: Save as `daily_scan.py` and run `python daily_scan.py`

---

### Task 2: Backtest a Symbol

**What**: Test strategy on historical data

```python
from tradingagents.dataflows.backtester import Backtester
from tradingagents.dataflows.report_generator import ReportGenerator
from datetime import datetime

symbol = "SPY"

# Run backtest (last 6 months)
backtester = Backtester(
    min_signal_score=70.0,   # Only trade signals >= 70/100
    risk_per_trade=2.0,       # Risk 2% per trade
    rr_ratio=2.0,             # Target 2:1 R:R
    max_bars_held=20          # Force exit after 20 days
)

result = backtester.run_backtest(
    symbol=symbol,
    start_date=datetime(2024, 8, 1),
    end_date=datetime(2025, 2, 1)
)

# Print results
print(f"\n{'='*50}")
print(f"Backtest Results: {symbol}")
print(f"{'='*50}")
print(f"Total Trades: {result.total_trades}")
print(f"Win Rate: {result.win_rate:.1f}%")
print(f"Profit Factor: {result.profit_factor:.2f}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.max_drawdown:.1f}%")
print(f"Total P&L: ${result.total_pnl:.2f}")

# Generate report
generator = ReportGenerator()
generator.generate_backtest_report(
    result=result,
    output_path=f"reports/{symbol}_backtest.html"
)

print(f"\n✅ Report saved: reports/{symbol}_backtest.html")
```

**Run**: `python backtest_symbol.py`

---

### Task 3: Send Manual Alert

**What**: Test alert system with a mock signal

```python
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig
from tradingagents.dataflows.scoring_engine import SignalScore, TradeDirection

# Create test signal
test_signal = SignalScore(
    symbol="TEST",
    direction=TradeDirection.LONG,
    total_score=85.0,
    trend_strength=90.0,
    direction_confluence=85.0,
    volume_quality=80.0,
    structure_quality=85.0,
    risk_profile=85.0,
    adx_value=35.0,
    volume_ratio=1.5,
    pct_from_200sma=2.5,
    atr_pct=1.8,
    weekly_trend=1,
    strengths=["Strong trend", "High volume", "Good structure"],
    weaknesses=["None significant"]
)

# Send alert
alert_system = AlertSystem(AlertConfig())
success = alert_system.send_signal_alert(
    signal=test_signal,
    alert_reason="Testing alert system"
)

if success:
    print("✅ Alert sent successfully!")
else:
    print("⚠️ No alert channels configured")
    print("   Set DISCORD_WEBHOOK_URL or EMAIL_* environment variables")
```

**Run**: `python test_alert.py`

---

### Task 4: Generate Weekly Report

**What**: Comprehensive report for weekend analysis

```python
from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow

# Run weekly workflow
# Scans 50+ symbols, generates report, emails summary
signals = example_c_weekly_workflow()

print(f"✅ Weekly workflow complete!")
print(f"   Found {len([s for s in signals if s.total_score >= 70])} strong setups")
```

**Run**: `python -c "from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow; example_c_weekly_workflow()"`

---

## API Reference

### Backtester

```python
from tradingagents.dataflows.backtester import Backtester

backtester = Backtester(
    min_signal_score=70.0,      # Minimum score to enter trade (0-100)
    risk_per_trade=2.0,          # % of capital risked per trade
    rr_ratio=2.0,                # Risk:Reward ratio (2.0 = 2:1)
    max_bars_held=20,            # Force exit after N bars
    use_trailing_stop=False      # Use trailing stop (not implemented)
)

result = backtester.run_backtest(
    symbol="SPY",                     # Symbol to test
    start_date=datetime(2024, 1, 1),  # Start date
    end_date=datetime(2025, 1, 1),    # End date
    direction=None                     # "LONG", "SHORT", or None (both)
)

# Export to JSON
backtester.export_results(result, "backtest.json")
```

**Result Attributes**:
- `result.total_trades`: Total number of trades
- `result.win_rate`: Win rate percentage (0-100)
- `result.profit_factor`: Total wins / abs(total losses)
- `result.sharpe_ratio`: Risk-adjusted return
- `result.max_drawdown`: Maximum equity decline %
- `result.total_pnl`: Total profit/loss in $

### Report Generator

```python
from tradingagents.dataflows.report_generator import ReportGenerator

generator = ReportGenerator()

# Screener report (multi-symbol)
html = generator.generate_screener_report(
    symbols=["SPY", "QQQ", "AAPL"],    # Symbols to include
    output_path="report.html",          # Output file path
    title="Daily Screener",             # Report title
    min_score=50.0                      # Minimum score filter
)

# Backtest report (single backtest)
html = generator.generate_backtest_report(
    result=backtest_result,             # BacktestResult object
    output_path="backtest.html"         # Output file path
)
```

### Alert System

```python
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig

# Configure via environment variables
config = AlertConfig()

# Or explicit config
config = AlertConfig(
    discord_webhook_url="https://discord.com/api/webhooks/...",
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    email_from="your@email.com",
    email_password="app_password",
    email_to=["recipient@example.com"]
)

alert_system = AlertSystem(config)

# Single alert
success = alert_system.send_signal_alert(
    signal=signal,                      # SignalScore object
    alert_reason="Strong setup"         # Reason for alert
)

# Batch alerts (multiple signals)
count = alert_system.send_batch_alerts(
    signals=[signal1, signal2, ...],    # List of SignalScore
    min_score=75.0                      # Only alert if >= threshold
)

# Daily summary email
alert_system.send_daily_summary(
    signals=[signal1, signal2, ...],    # List of signals
    report_path="report.html"           # Optional attachment
)

# Check alert history
history = alert_system.get_alert_history(hours=24)
for alert in history:
    print(f"{alert['timestamp']}: {alert['symbol']} {alert['direction']}")
```

---

## Integration Examples

### Example A: Morning Scan Workflow

```python
# File: daily_scan.py
from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow

signals = example_a_daily_workflow()
```

**What it does**:
1. Scans watchlist (20-30 symbols)
2. Scores each symbol
3. Generates HTML report
4. Sends alerts for signals >= 75/100

**Schedule**: Run at 8:00 AM ET daily
```bash
# Linux/Mac cron
0 8 * * 1-5 cd /path/to/TradingAgents && python -c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"

# Windows Task Scheduler
# Create task to run daily at 8:00 AM
# Action: python -c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"
```

### Example B: Backtest Before Going Live

```python
# File: validate_strategy.py
from tradingagents.dataflows.fase3_integration_examples import example_b_backtest_validation

results = example_b_backtest_validation(["SPY", "QQQ", "IWM"])
```

**What it does**:
1. Runs backtest on last 6 months
2. Calculates performance metrics
3. Generates HTML reports

**When to run**: Before deploying any strategy changes

### Example C: Weekend Planning

```python
# File: weekly_report.py
from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow

signals = example_c_weekly_workflow()
```

**What it does**:
1. Scans 50+ symbols
2. Generates comprehensive report
3. Emails summary to team

**Schedule**: Sunday evening at 8:00 PM ET

### Example D: Live Monitoring

```python
# File: monitor.py
from tradingagents.dataflows.fase3_integration_examples import example_d_live_monitoring

# Monitor specific symbols every 30 minutes
signals = example_d_live_monitoring(
    watchlist=["SPY", "QQQ", "AAPL"],
    check_interval_minutes=30
)
```

**What it does**:
1. Rescans symbols every N minutes
2. Detects new signals crossing threshold
3. Sends immediate alerts
4. Rate limiting prevents spam

**Schedule**: During market hours (9:30 AM - 4:00 PM ET)

---

## Performance Tips

### 1. Use Caching
```python
# FASE 2 automatically caches data for 5 minutes
mtf = MultiTimeframeLayer()

# First call: fetches from API
mtf_data = mtf.get_multi_timeframe_data("SPY")  

# Subsequent calls within 5 min: returns cached data
mtf_data = mtf.get_multi_timeframe_data("SPY")
```

### 2. Batch Operations
```python
# Bad: Generate separate report for each symbol
for symbol in watchlist:
    generator.generate_screener_report([symbol], f"report_{symbol}.html")

# Good: Generate single report for all symbols
generator.generate_screener_report(watchlist, "report_all.html")
```

### 3. Respect API Limits
```python
import time

for symbol in large_watchlist:
    try:
        mtf_data = mtf.get_multi_timeframe_data(symbol)
    except Exception as e:
        if "rate limit" in str(e).lower():
            time.sleep(60)  # Wait 1 minute
```

### 4. Filter Before Processing
```python
# Filter out low-volume stocks before scoring
from tradingagents.dataflows.y_finance import YFinanceDataProvider

provider = YFinanceDataProvider()

filtered_watchlist = []
for symbol in watchlist:
    try:
        daily_df = provider.get_daily_data(symbol, period="1d")
        volume = daily_df['Volume'].iloc[-1]
        
        if volume > 1_000_000:  # Only symbols with >1M daily volume
            filtered_watchlist.append(symbol)
    except:
        pass

# Now score only liquid symbols
for symbol in filtered_watchlist:
    # ... score ...
```

---

## Troubleshooting

### Issue: "No module named 'tradingagents'"

**Solution**:
```bash
# Make sure you're in the right directory
cd /path/to/TradingAgents

# Install in development mode
pip install -e .
```

### Issue: "Rate limit exceeded"

**Solution**:
```python
# Add delay between API calls
import time

for symbol in watchlist:
    mtf_data = mtf.get_multi_timeframe_data(symbol)
    time.sleep(12)  # 5 calls/min = 12 sec between calls
```

### Issue: Discord webhook not working

**Test webhook**:
```bash
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'
```

If that works, check webhook URL in config.

### Issue: Gmail authentication error

**Solution**:
1. Enable 2FA on Gmail
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate app password
4. Use that instead of regular password

### Issue: Backtest generates no trades

**Check 1**: Lower score threshold
```python
backtester = Backtester(min_signal_score=60.0)  # Was 70.0
```

**Check 2**: Verify data availability
```python
from tradingagents.dataflows.y_finance import YFinanceDataProvider

provider = YFinanceDataProvider()
df = provider.get_daily_data("SPY", period="6mo")
print(f"Data points: {len(df)}")  # Should be ~120-130
```

### Issue: Report charts not displaying

**Check 1**: Plotly installed
```bash
pip install plotly
```

**Check 2**: Open in browser (not text editor)
```bash
# Linux/Mac
open report.html

# Windows
start report.html
```

---

## Environment Variables Reference

```bash
# Discord alerts
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK"

# Email alerts (Gmail)
export EMAIL_FROM="your@gmail.com"
export EMAIL_PASSWORD="app_specific_password"
export EMAIL_TO="recipient@example.com"

# Email alerts (Outlook)
export EMAIL_FROM="your@outlook.com"
export EMAIL_PASSWORD="your_password"
export EMAIL_TO="recipient@example.com"
export SMTP_SERVER="smtp.office365.com"
export SMTP_PORT="587"

# Data sources
export ALPHA_VANTAGE_API_KEY="your_key"
```

**Permanent setup** (Linux/Mac):
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export DISCORD_WEBHOOK_URL="..."' >> ~/.bashrc
source ~/.bashrc
```

**Permanent setup** (Windows):
```powershell
# PowerShell
[Environment]::SetEnvironmentVariable("DISCORD_WEBHOOK_URL", "...", "User")
```

---

## Scheduling

### Linux/Mac (cron)

```bash
# Edit crontab
crontab -e

# Add jobs (runs at 8:00 AM on weekdays)
0 8 * * 1-5 cd /path/to/TradingAgents && python -c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"

# Sunday evening report (8:00 PM)
0 20 * * 0 cd /path/to/TradingAgents && python -c "from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow; example_c_weekly_workflow()"
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Task → "Daily Market Scan"
3. Triggers: Daily at 8:00 AM, weekdays only
4. Actions: Start a program
   - Program: `python`
   - Arguments: `-c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"`
   - Start in: `C:\path\to\TradingAgents`

---

## Next Steps

1. **Run test suite**: `python test_fase3_infrastructure.py`
2. **Try examples**: Run each example in `fase3_integration_examples.py`
3. **Backtest your watchlist**: Validate strategy performance
4. **Set up alerts**: Configure Discord/Email
5. **Schedule daily scan**: Set up cron/Task Scheduler
6. **Review FASE3_ARCHITECTURE.md**: Deep dive into implementation

---

## Support

- **Documentation**: `docs/FASE3_ARCHITECTURE.md`
- **Examples**: `tradingagents/dataflows/fase3_integration_examples.py`
- **Tests**: `test_fase3_infrastructure.py`
- **Issues**: Check error messages and logs

**Common Commands**:
```bash
# Run tests
python test_fase3_infrastructure.py

# Run daily workflow
python -c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"

# Backtest symbol
python -c "from tradingagents.dataflows.fase3_integration_examples import example_b_backtest_validation; example_b_backtest_validation(['SPY'])"

# Check environment
echo $DISCORD_WEBHOOK_URL
echo $EMAIL_FROM
```
