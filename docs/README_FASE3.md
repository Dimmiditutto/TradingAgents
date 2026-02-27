# FASE 3: Testing & Reporting Infrastructure

Complete documentation for TradingAgents backtesting, reporting, and alerting layer.

---

## Overview

FASE 3 adds production-ready infrastructure for:
- **Backtesting**: Historical validation with walk-forward simulation
- **Reports**: Professional HTML reports with interactive charts
- **Alerts**: Real-time notifications via Discord and Email

This completes the swing trading system, enabling systematic validation and deployment.

---

## Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| [Quick Reference](FASE3_QUICK_REFERENCE.md) | Get started in 5 minutes | Everyone |
| [Architecture](FASE3_ARCHITECTURE.md) | Deep technical details | Developers |
| [Deployment Checklist](FASE3_DEPLOYMENT_CHECKLIST.md) | Production deployment | Operators |
| [Integration Examples](../tradingagents/dataflows/fase3_integration_examples.py) | Complete workflows | Users |
| [Test Suite](../test_fase3_infrastructure.py) | Validation tests | QA |

---

## What's New in FASE 3

### Module 1: Backtester (580 lines)
- Walk-forward historical simulation
- Entry/exit logic based on signal scores
- Performance metrics (win rate, Sharpe, drawdown)
- Trade-by-trade analysis
- JSON export for further analysis

### Module 2: Report Generator (720 lines)
- Multi-symbol screener reports
- Interactive Plotly charts (candlesticks, volume, ADX)
- Responsive HTML with modern CSS
- Score breakdown and strength/weakness analysis
- Backtest performance reports

### Module 3: Alert System (680 lines)
- Discord webhook integration with embeds
- SMTP email with HTML formatting
- Rate limiting (1 alert per symbol/hour)
- Batch alerts for multiple signals
- Daily summary emails with attachments

### Total: 1,980 lines of production code

---

## Getting Started

### 1. Install Dependencies
```bash
pip install requests plotly pandas numpy yfinance alpha_vantage
```

### 2. Run Test Suite
```bash
python test_fase3_infrastructure.py
```

Expected output: All 7 tests pass ✅

### 3. Try an Example
```python
from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow

# Run daily morning scan
signals = example_a_daily_workflow()
```

### 4. Review Report
Open `reports/daily_screener_YYYYMMDD_HHMMSS.html` in browser.

### 5. Configure Alerts (Optional)
```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export EMAIL_FROM="your@email.com"
export EMAIL_PASSWORD="app_password"
export EMAIL_TO="recipient@example.com"
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     FASE 3 Layer                         │
│                                                          │
│  ┌───────────┐   ┌────────────────┐   ┌──────────────┐ │
│  │Backtester │   │ReportGenerator │   │ AlertSystem  │ │
│  │           │   │                │   │              │ │
│  │• Walk-    │   │• HTML exports  │   │• Discord     │ │
│  │  forward  │   │• Plotly charts │   │• Email       │ │
│  │• Trade    │   │• Responsive    │   │• Rate        │ │
│  │  sim      │   │  CSS           │   │  limiting    │ │
│  │• Metrics  │   │• Multi-symbol  │   │• History     │ │
│  └─────┬─────┘   └────────┬───────┘   └──────┬───────┘ │
│        │                  │                   │          │
└────────┼──────────────────┼───────────────────┼──────────┘
         │                  │                   │
         ↓                  ↓                   ↓
┌──────────────────────────────────────────────────────────┐
│                      FASE 2 Layer                         │
│  (Multi-Timeframe, Scoring, Structure Detection)         │
│                                                           │
│  MultiTimeframeLayer → ScoringEngine → SignalScore       │
│         ↓                    ↓              ↓             │
│    Weekly/Daily          0-100 Score   LONG/SHORT        │
└──────────────────────────────────────────────────────────┘
```

---

## Core Workflows

### Daily Morning Scan (8:00 AM)
```python
from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow

signals = example_a_daily_workflow()
```

**What it does**:
1. Scans 20-30 symbol watchlist
2. Scores each with FASE 2 engine
3. Generates HTML screener report
4. Sends alerts for signals >= 75/100

**Output**: 
- `reports/daily_screener_YYYYMMDD_HHMMSS.html`
- Discord/Email alerts (if configured)

**Time**: 5-10 minutes

### Backtest Validation
```python
from tradingagents.dataflows.fase3_integration_examples import example_b_backtest_validation

results = example_b_backtest_validation(["SPY", "QQQ", "IWM"])
```

**What it does**:
1. Runs backtest on last 6 months
2. Simulates trades based on signal scores
3. Calculates performance metrics
4. Generates HTML backtest reports

**Output**:
- `reports/backtests/SPY_backtest_YYYYMMDD_HHMMSS.html`
- Console summary with metrics

**Time**: 2-5 minutes per symbol

### Weekly Deep Dive (Sunday 8:00 PM)
```python
from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow

signals = example_c_weekly_workflow()
```

**What it does**:
1. Scans 50+ symbol watchlist
2. Generates comprehensive report
3. Emails summary to team

**Output**:
- `reports/weekly_outlook_YYYYMMDD.html`
- Email with attachment

**Time**: 15-20 minutes

### Live Monitoring
```python
from tradingagents.dataflows.fase3_integration_examples import example_d_live_monitoring

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

**Time**: Continuous (background process)

---

## Key Features

### Backtester

**Entry Logic**:
- Signal score >= min_signal_score (default: 70/100)
- Stop loss from structure detection (swing lows/highs)
- Take profit = entry ± (risk × RR_ratio) [default: 2:1]

**Exit Logic**:
- Stop hit
- Target hit
- Max bars held (default: 20)
- Signal reversal

**Metrics**:
- Win rate (%)
- Profit factor (wins/losses)
- Sharpe ratio (risk-adjusted return)
- Max drawdown (%)
- Max consecutive losses

### Report Generator

**Screener Report**:
- Summary cards (total signals, strong LONG/SHORT, avg score)
- Signal cards with:
  - Score badge (color-coded by strength)
  - Score breakdown (5 components)
  - Key metrics (ADX, VR, ATR%, % from 200 SMA)
  - Strengths and weaknesses
  - Interactive Plotly chart

**Chart Structure** (3-row subplot):
1. Price action (candlesticks, 200 SMA, SuperTrend)
2. Volume (colored bars)
3. ADX (with 25 threshold)

**Backtest Report**:
- Performance metrics grid
- Trade log table (sortable)
- P&L distribution
- Exit reason breakdown

### Alert System

**Discord Integration**:
- Webhook POST with embeds
- Color-coded (green=LONG, red=SHORT)
- Score breakdown
- Strengths/weaknesses
- Timestamp

**Email Integration**:
- SMTP with TLS
- Multipart MIME (HTML + plain text)
- Styled HTML with tables
- Plain text fallback

**Rate Limiting**:
- 1 alert per symbol/direction per hour
- Prevents spam during volatile markets
- Alert history tracking

---

## Performance

### Caching
FASE 2 cache manager reduces API calls by ~50%:
- 5-minute cache for MTF data
- Automatic cache invalidation
- Manual cache clearing available

### Batch Operations
Process multiple symbols efficiently:
- Single screener report vs multiple individual reports
- Batch alerts vs single alerts
- Reduced API calls

### API Respect
Stay within rate limits:
- Alpha Vantage: 5 calls/min (free), 75 calls/min (premium)
- yfinance: ~2000 calls/hour recommended
- Automatic retry with backoff

---

## Testing

### Test Suite Coverage

7 comprehensive tests:

1. **Trade Class**: P&L calculation for LONG/SHORT trades
2. **BacktestResult**: Metrics computation (win rate, profit factor, etc.)
3. **Backtester**: Historical simulation with real data
4. **Report Generator**: HTML generation and chart creation
5. **Alert Configuration**: Environment variables and explicit config
6. **Alert System**: Discord and Email formatting
7. **Full Integration**: Complete workflow (score → backtest → report → alert)

### Running Tests
```bash
python test_fase3_infrastructure.py
```

Expected: ✅ All 7 tests pass

### Manual Testing
```python
# Test backtester
from tradingagents.dataflows.backtester import Backtester
from datetime import datetime

backtester = Backtester()
result = backtester.run_backtest("SPY", datetime(2024, 8, 1), datetime(2025, 2, 1))
print(f"Trades: {result.total_trades}, Win Rate: {result.win_rate:.1f}%")

# Test report generator
from tradingagents.dataflows.report_generator import ReportGenerator

generator = ReportGenerator()
generator.generate_screener_report(["SPY"], "test_report.html", "Test")

# Test alert system
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig

alert_system = AlertSystem(AlertConfig())
# ... create test signal ...
alert_system.send_signal_alert(test_signal, "Test")
```

---

## Documentation

### For Users
- **[Quick Reference](FASE3_QUICK_REFERENCE.md)**: Get started in 5 minutes
  - Installation
  - Common tasks
  - API reference
  - Troubleshooting

### For Developers
- **[Architecture](FASE3_ARCHITECTURE.md)**: Deep technical dive
  - Module design
  - Class structures
  - Algorithms
  - Integration points

### For Operations
- **[Deployment Checklist](FASE3_DEPLOYMENT_CHECKLIST.md)**: Production deployment
  - Pre-deployment verification
  - Scheduling setup
  - Monitoring configuration
  - Maintenance tasks
  - Rollback procedures

### Code Examples
- **[Integration Examples](../tradingagents/dataflows/fase3_integration_examples.py)**: Complete workflows
  - Daily morning scan
  - Backtest validation
  - Weekly deep dive
  - Live monitoring

---

## Dependencies

### Required Packages
```
requests>=2.31.0       # Discord webhook
plotly>=5.18.0         # Interactive charts
pandas>=2.0.0          # Data manipulation
numpy>=1.24.0          # Numerical computing
yfinance>=0.2.0        # Market data
alpha_vantage>=2.3.1   # Market data (optional)
```

### Environment Variables
```bash
# Alerts (optional)
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
EMAIL_FROM="your@email.com"
EMAIL_PASSWORD="app_specific_password"
EMAIL_TO="recipient@example.com"

# Data sources
ALPHA_VANTAGE_API_KEY="your_key"
```

---

## Troubleshooting

### Common Issues

**No trades in backtest**:
- Lower `min_signal_score` (try 60.0 instead of 70.0)
- Verify data availability (check yfinance connection)

**Report charts not displaying**:
- Ensure Plotly installed: `pip install plotly`
- Open in browser (not text editor)

**Discord alerts not working**:
- Verify webhook URL format
- Test with curl: `curl -X POST webhook_url -H "Content-Type: application/json" -d '{"content":"test"}'`

**Email authentication failure**:
- Gmail: Use app password (not account password)
- Enable 2FA first
- Generate at: myaccount.google.com/apppasswords

**Rate limiting too aggressive**:
- Adjust in `alert_system.py`: Change `timedelta(hours=1)` to `timedelta(minutes=30)`

See [Quick Reference](FASE3_QUICK_REFERENCE.md) for more troubleshooting.

---

## Scheduling

### Linux/Mac (cron)
```bash
crontab -e

# Daily scan at 8:00 AM ET (weekdays)
0 8 * * 1-5 cd /path/to/TradingAgents && python -c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"

# Weekly report at 8:00 PM ET (Sunday)
0 20 * * 0 cd /path/to/TradingAgents && python -c "from tradingagents.dataflows.fase3_integration_examples import example_c_weekly_workflow; example_c_weekly_workflow()"
```

### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Task → "Daily Market Scan"
3. Trigger: Daily at 8:00 AM, weekdays only
4. Action: Start a program
   - Program: `python`
   - Arguments: `-c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"`
   - Start in: `C:\path\to\TradingAgents`

See [Deployment Checklist](FASE3_DEPLOYMENT_CHECKLIST.md) for complete setup.

---

## Roadmap

### FASE 3 Complete ✅
- Backtesting framework
- Report generation
- Alert system
- Integration examples
- Documentation
- Test suite

### FASE 4 Planning (Future)
- Trade execution (broker API integration)
- Portfolio management
- Position sizing algorithms
- Risk management enforcement
- Performance tracking dashboard
- Machine learning score optimization

---

## File Structure

```
TradingAgents/
├── tradingagents/
│   └── dataflows/
│       ├── backtester.py                     (580 lines) ✅
│       ├── report_generator.py               (720 lines) ✅
│       ├── alert_system.py                   (680 lines) ✅
│       └── fase3_integration_examples.py     (500 lines) ✅
├── docs/
│   ├── README_FASE3.md                       (this file) ✅
│   ├── FASE3_ARCHITECTURE.md                 (1,200 lines) ✅
│   ├── FASE3_QUICK_REFERENCE.md              (800 lines) ✅
│   └── FASE3_DEPLOYMENT_CHECKLIST.md         (900 lines) ✅
├── test_fase3_infrastructure.py              (400 lines) ✅
└── reports/                                  (output dir)
    ├── daily_screener_YYYYMMDD_HHMMSS.html
    ├── weekly_outlook_YYYYMMDD.html
    └── backtests/
        └── SYMBOL_backtest_YYYYMMDD_HHMMSS.html
```

**Total**: ~5,780 lines (code + docs)

---

## Success Metrics

After deploying FASE 3, you should achieve:

### Week 1
- [ ] 5 daily reports generated (Mon-Fri)
- [ ] 1 weekly report generated (Sunday)
- [ ] 5-20 alerts sent (depending on market)
- [ ] No critical errors in logs

### Month 1
- [ ] 20+ daily reports
- [ ] 4 weekly reports
- [ ] Performance tracking data collected
- [ ] Initial validation complete

### Quarter 1
- [ ] 60+ daily reports
- [ ] 12 weekly reports
- [ ] Statistical validation of signal quality
- [ ] Parameter optimization based on real results

---

## Support

**Documentation**:
- Quick Reference: [FASE3_QUICK_REFERENCE.md](FASE3_QUICK_REFERENCE.md)
- Architecture: [FASE3_ARCHITECTURE.md](FASE3_ARCHITECTURE.md)
- Deployment: [FASE3_DEPLOYMENT_CHECKLIST.md](FASE3_DEPLOYMENT_CHECKLIST.md)

**Code**:
- Examples: [fase3_integration_examples.py](../tradingagents/dataflows/fase3_integration_examples.py)
- Tests: [test_fase3_infrastructure.py](../test_fase3_infrastructure.py)

**Quick Commands**:
```bash
# Run tests
python test_fase3_infrastructure.py

# Daily workflow
python -c "from tradingagents.dataflows.fase3_integration_examples import example_a_daily_workflow; example_a_daily_workflow()"

# Backtest validation
python -c "from tradingagents.dataflows.fase3_integration_examples import example_b_backtest_validation; example_b_backtest_validation(['SPY', 'QQQ'])"

# Check environment
echo $DISCORD_WEBHOOK_URL
echo $EMAIL_FROM
```

---

## Version History

### v1.0 (Current - February 2025)
- Initial FASE 3 release
- Backtester: 580 lines
- Report Generator: 720 lines
- Alert System: 680 lines
- Complete documentation: 3,800+ lines
- Test suite: 400 lines
- Integration examples: 500 lines

**Status**: Production ready ✅

---

## License

See [LICENSE](../LICENSE) file for details.

---

## Acknowledgments

Built on FASE 2 infrastructure:
- Multi-timeframe data layer
- 44 technical indicators
- Signal scoring engine (0-100)
- Structure detection
- Cache management

FASE 3 completes the system with professional testing and reporting capabilities.

---

## Next Steps

1. **Read**: [Quick Reference](FASE3_QUICK_REFERENCE.md) (5 minutes)
2. **Test**: Run `python test_fase3_infrastructure.py`
3. **Try**: Execute an example workflow
4. **Deploy**: Follow [Deployment Checklist](FASE3_DEPLOYMENT_CHECKLIST.md)
5. **Monitor**: Track performance for 1 week
6. **Optimize**: Adjust parameters based on results

**Ready to go live?** 🚀

Follow the [Deployment Checklist](FASE3_DEPLOYMENT_CHECKLIST.md) for production deployment.
