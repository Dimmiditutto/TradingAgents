# FASE 3: Testing & Reporting Infrastructure

## Overview

FASE 3 completes the TradingAgents swing trading system by adding:
- **Backtesting**: Historical validation of signal scoring strategy
- **Report Generation**: Professional HTML reports with charts
- **Alert System**: Real-time notifications via Discord and Email

This infrastructure enables systematic validation, daily monitoring, and production deployment.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FASE 3 Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │   Backtester    │  │ ReportGenerator  │  │ AlertSystem│ │
│  │                 │  │                  │  │            │ │
│  │ • Walk-forward  │  │ • HTML exports   │  │ • Discord  │ │
│  │ • Trade sim     │  │ • Plotly charts  │  │ • Email    │ │
│  │ • Performance   │  │ • Responsive CSS │  │ • Rate     │ │
│  │   metrics       │  │ • Multi-symbol   │  │   limiting │ │
│  └────────┬────────┘  └────────┬─────────┘  └─────┬──────┘ │
│           │                    │                   │        │
└───────────┼────────────────────┼───────────────────┼────────┘
            │                    │                   │
            ↓                    ↓                   ↓
┌───────────────────────────────────────────────────────────────┐
│                       FASE 2 Layer                             │
│  (Multi-Timeframe, Scoring Engine, Structure Detection)       │
└───────────────────────────────────────────────────────────────┘
```

---

## Module 1: Backtester

**File**: `tradingagents/dataflows/backtester.py` (580 lines)

### Purpose

Historical validation using walk-forward simulation with lookahead bias prevention.

### Classes

#### Trade (dataclass)
```python
@dataclass
class Trade:
    symbol: str
    direction: str              # "LONG" or "SHORT"
    entry_date: datetime
    entry_price: float
    entry_signal_score: float   # 0-100
    stop_loss: float
    take_profit: float
    
    # Exit data (filled on close)
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # "TARGET", "STOP", "TIME", "SIGNAL"
    pnl: float = 0.0
    pnl_pct: float = 0.0
    bars_held: int = 0
    
    # Context
    entry_adx: Optional[float] = None
    entry_volume_ratio: Optional[float] = None
    entry_structure: Optional[str] = None
    status: str = "OPEN"
```

**Methods**:
- `close_trade(exit_date, exit_price, reason)`: Calculate P&L and duration
- `to_dict()`: Export as dictionary

#### BacktestResult (dataclass)
```python
@dataclass
class BacktestResult:
    symbol: str
    start_date: datetime
    end_date: datetime
    trades: List[Trade] = field(default_factory=list)
    
    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_consecutive_losses: int = 0
    avg_bars_held: float = 0.0
```

**Methods**:
- `calculate_metrics()`: Compute all performance statistics
- `to_dict()`: Export summary

#### Backtester

Main backtesting engine.

```python
class Backtester:
    def __init__(
        self,
        min_signal_score: float = 70.0,    # Minimum score to trade
        risk_per_trade: float = 2.0,        # % of capital per trade
        rr_ratio: float = 2.0,              # Risk:Reward ratio
        max_bars_held: int = 20,            # Force exit after N bars
        use_trailing_stop: bool = False
    )
```

**Methods**:
- `run_backtest(symbol, start_date, end_date, direction=None)`: Execute simulation
- `export_results(result, output_path)`: Save to JSON

### Entry/Exit Logic

#### Entry Rules
```python
if signal_score >= min_signal_score:
    # Enter trade
    entry_price = current_close
    
    # Calculate stop from structure
    if direction == "LONG":
        stop_loss = recent_swing_low
    else:
        stop_loss = recent_swing_high
    
    # Calculate target
    risk = abs(entry_price - stop_loss)
    take_profit = entry_price + (risk * rr_ratio)  # For LONG
```

#### Exit Rules

Checked on every bar:

1. **Stop Hit**: Price <= stop_loss (LONG) or >= stop_loss (SHORT)
2. **Target Hit**: Price >= take_profit (LONG) or <= take_profit (SHORT)
3. **Time Exit**: bars_held >= max_bars_held
4. **Signal Reversal**: New opposite signal >= min_signal_score

### Performance Metrics

**Win Rate**:
```
win_rate = (winning_trades / total_trades) × 100
```

**Profit Factor**:
```
profit_factor = sum(winning_pnl) / abs(sum(losing_pnl))
```

**Sharpe Ratio**:
```
sharpe_ratio = mean(returns) / std(returns) × sqrt(252)
```

**Max Drawdown**:
```
max_drawdown = max(peak - trough) / peak × 100
```

**Max Consecutive Losses**:
```
Track longest losing streak
```

### Usage Example

```python
from tradingagents.dataflows.backtester import Backtester
from datetime import datetime

backtester = Backtester(
    min_signal_score=70.0,
    risk_per_trade=2.0,
    rr_ratio=2.0,
    max_bars_held=20
)

result = backtester.run_backtest(
    symbol="SPY",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2025, 1, 1)
)

print(f"Total Trades: {result.total_trades}")
print(f"Win Rate: {result.win_rate:.1f}%")
print(f"Profit Factor: {result.profit_factor:.2f}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")

# Export to JSON
backtester.export_results(result, "backtest_results.json")
```

---

## Module 2: Report Generator

**File**: `tradingagents/dataflows/report_generator.py` (720 lines)

### Purpose

Generate professional HTML reports with interactive Plotly charts.

### Classes

#### ReportGenerator

```python
class ReportGenerator:
    def __init__(self)
```

**Methods**:

1. **Screener Report**:
```python
def generate_screener_report(
    self,
    symbols: List[str],
    output_path: str,
    title: str = "Market Screener",
    min_score: float = 50.0
) -> str
```

Generates multi-symbol ranked report showing:
- Summary statistics (total signals, strong setups, avg score)
- Signal cards for each symbol (sorted by score)
- Interactive Plotly charts
- Strength/weakness analysis

2. **Backtest Report**:
```python
def generate_backtest_report(
    self,
    result: BacktestResult,
    output_path: str
) -> str
```

Generates historical performance report showing:
- Performance metrics grid
- Trade log table (sortable)
- P&L distribution
- Exit reason breakdown

### Report Structure

#### Screener Report Layout

```html
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>/* Embedded CSS */</style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>{title}</h1>
        <p>{timestamp}</p>
    </div>
    
    <!-- Summary Cards -->
    <div class="summary-section">
        <div class="summary-card">
            <h3>Total Signals</h3>
            <p class="summary-value">{count}</p>
        </div>
        <div class="summary-card">
            <h3>Strong LONG</h3>
            <p class="summary-value">{long_count}</p>
        </div>
        <div class="summary-card">
            <h3>Strong SHORT</h3>
            <p class="summary-value">{short_count}</p>
        </div>
        <div class="summary-card">
            <h3>Avg Score</h3>
            <p class="summary-value">{avg_score}/100</p>
        </div>
    </div>
    
    <!-- Signal Cards -->
    <div class="signals-grid">
        {for each signal}
        <div class="signal-card">
            <div class="signal-header">
                <h2>{symbol}</h2>
                <span class="badge {direction}">{direction}</span>
            </div>
            
            <div class="score-section">
                <div class="total-score">{total_score}/100</div>
                <div class="score-breakdown">
                    • Trend Strength: {trend}/100
                    • Confluence: {conf}/100
                    • Volume: {vol}/100
                    • Structure: {struct}/100
                    • Risk Profile: {risk}/100
                </div>
            </div>
            
            <div class="metrics-grid">
                <div>ADX: {adx}</div>
                <div>Volume Ratio: {vr}</div>
                <div>ATR%: {atr}%</div>
                <div>% from 200 SMA: {pct}%</div>
            </div>
            
            <div class="strengths">
                <h4>Strengths</h4>
                <ul>{strengths}</ul>
            </div>
            
            <div class="weaknesses">
                <h4>Weaknesses</h4>
                <ul>{weaknesses}</ul>
            </div>
            
            <!-- Plotly Chart -->
            <div class="chart">{plotly_html}</div>
        </div>
        {end for}
    </div>
</body>
</html>
```

### Plotly Chart Structure

3-row subplot layout:

**Row 1 (60% height)**: Price Action
- Candlesticks (green/red)
- 200 SMA (blue line)
- SuperTrend (purple dashed)

**Row 2 (20% height)**: Volume
- Volume bars colored by direction

**Row 3 (20% height)**: ADX
- ADX line with 25 threshold

```python
fig = make_subplots(
    rows=3, cols=1,
    row_heights=[0.6, 0.2, 0.2],
    shared_xaxes=True,
    vertical_spacing=0.05
)

# Add candlesticks
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ),
    row=1, col=1
)

# Add indicators...
```

### CSS Styling

**Theme**: Purple gradient (`#667eea` → `#764ba2`)

**Layout**: Responsive grid
```css
.signals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
}
```

**Cards**: Hover effects
```css
.signal-card {
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}

.signal-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
```

**Score Badges**:
- LONG: Green (`#28a745`)
- SHORT: Red (`#dc3545`)
- Gradient by strength (90+ = darker, 50-70 = lighter)

### Usage Example

```python
from tradingagents.dataflows.report_generator import ReportGenerator

generator = ReportGenerator()

# Generate screener report
generator.generate_screener_report(
    symbols=["SPY", "QQQ", "AAPL", "MSFT"],
    output_path="reports/daily_screener.html",
    title="Daily Market Screener",
    min_score=50.0
)

# Generate backtest report
generator.generate_backtest_report(
    result=backtest_result,
    output_path="reports/spy_backtest.html"
)
```

---

## Module 3: Alert System

**File**: `tradingagents/dataflows/alert_system.py` (680 lines)

### Purpose

Real-time notifications via Discord webhooks and SMTP email.

### Classes

#### AlertConfig

```python
@dataclass
class AlertConfig:
    # Discord
    discord_webhook_url: Optional[str] = None
    
    # Email (SMTP)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_from: Optional[str] = None
    email_password: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
```

**Methods**:
- `is_discord_enabled()`: Check if Discord configured
- `is_email_enabled()`: Check if email configured

**Environment Variables**:
```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export EMAIL_FROM="your@email.com"
export EMAIL_PASSWORD="app_password"  # Not regular password!
export EMAIL_TO="recipient1@email.com,recipient2@email.com"
```

#### AlertSystem

```python
class AlertSystem:
    def __init__(self, config: AlertConfig)
```

**Methods**:

1. **Single Signal Alert**:
```python
def send_signal_alert(
    self,
    signal: SignalScore,
    alert_reason: str = "Signal threshold crossed"
) -> bool
```

Sends alert via configured channels (Discord and/or Email).

2. **Batch Alerts**:
```python
def send_batch_alerts(
    self,
    signals: List[SignalScore],
    min_score: float = 75.0
) -> int
```

Sends alerts for all signals above threshold. Returns count sent.

3. **Daily Summary**:
```python
def send_daily_summary(
    self,
    signals: List[SignalScore],
    report_path: Optional[str] = None
) -> bool
```

Email summary of day's signals (top 5) with optional HTML report attachment.

4. **Alert History**:
```python
def get_alert_history(
    self,
    hours: int = 24
) -> List[Dict]
```

Retrieve recent alert history.

### Discord Integration

**Webhook POST** with embed:

```python
embed = {
    "title": f"{emoji} {symbol} - {direction} Signal",
    "color": 0x28a745 if direction == "LONG" else 0xdc3545,
    "fields": [
        {"name": "Total Score", "value": f"{score}/100", "inline": True},
        {"name": "Trend Strength", "value": f"{trend}/100", "inline": True},
        {"name": "Confluence", "value": f"{conf}/100", "inline": True},
        {"name": "ADX", "value": f"{adx}", "inline": True},
        {"name": "Volume Ratio", "value": f"{vr}x", "inline": True},
        {"name": "ATR%", "value": f"{atr}%", "inline": True},
        {"name": "Strengths", "value": "\n".join(strengths[:3])},
        {"name": "Weaknesses", "value": "\n".join(weaknesses[:2])},
    ],
    "footer": {"text": "TradingAgents Alert System"},
    "timestamp": datetime.utcnow().isoformat()
}

requests.post(webhook_url, json={"embeds": [embed]})
```

**Colors**:
- LONG: `0x28a745` (green)
- SHORT: `0xdc3545` (red)

### Email Integration

**SMTP with TLS** (port 587):

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

msg = MIMEMultipart('alternative')
msg['Subject'] = f"🚨 {symbol} {direction} Signal - Score {score}/100"
msg['From'] = email_from
msg['To'] = ", ".join(email_to)

# Plain text version
text_content = f"""
{symbol} {direction} Signal Alert

Score: {score}/100
Trend Strength: {trend}/100
ADX: {adx}
Volume Ratio: {vr}x

Strengths:
{strengths}

Weaknesses:
{weaknesses}
"""

# HTML version with styling
html_content = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ 
            background: {'#28a745' if direction == 'LONG' else '#dc3545'}; 
            color: white; 
            padding: 20px; 
        }}
        table {{ border-collapse: collapse; width: 100%; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .strength {{ color: #28a745; }}
        .weakness {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>{symbol} {direction} Signal</h2>
        <p>Score: {score}/100</p>
    </div>
    
    <h3>Score Breakdown</h3>
    <table>
        <tr><td>Trend Strength</td><td>{trend}/100</td></tr>
        <tr><td>Confluence</td><td>{conf}/100</td></tr>
        ...
    </table>
    
    <h3 class="strength">Strengths</h3>
    <ul>{strengths_html}</ul>
    
    <h3 class="weakness">Weaknesses</h3>
    <ul>{weaknesses_html}</ul>
</body>
</html>
"""

msg.attach(MIMEText(text_content, 'plain'))
msg.attach(MIMEText(html_content, 'html'))

server = smtplib.SMTP(smtp_server, smtp_port)
server.starttls()
server.login(email_from, email_password)
server.sendmail(email_from, email_to, msg.as_string())
server.quit()
```

### Rate Limiting

Prevents spam: **1 alert per symbol/direction per hour**

```python
def _check_rate_limit(self, symbol: str, direction: str) -> bool:
    cache_key = f"{symbol}_{direction}"
    
    if cache_key in self.rate_limit_cache:
        last_alert = self.rate_limit_cache[cache_key]
        
        if datetime.now() - last_alert < timedelta(hours=1):
            # Already alerted within last hour
            return False
    
    # Update cache
    self.rate_limit_cache[cache_key] = datetime.now()
    return True
```

### Usage Example

```python
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig

# Configure via environment variables
config = AlertConfig()

# Or explicit configuration
config = AlertConfig(
    discord_webhook_url="https://discord.com/api/webhooks/...",
    email_from="trading@example.com",
    email_password="app_password",
    email_to=["trader1@example.com", "trader2@example.com"]
)

alert_system = AlertSystem(config)

# Send single alert
alert_system.send_signal_alert(
    signal=signal,
    alert_reason="Daily screener detected strong setup"
)

# Send batch alerts
count = alert_system.send_batch_alerts(
    signals=all_signals,
    min_score=75.0
)
print(f"Sent {count} alerts")

# Daily summary
alert_system.send_daily_summary(
    signals=strong_signals,
    report_path="reports/daily_screener.html"
)
```

---

## Integration with FASE 2

FASE 3 modules consume FASE 2 outputs:

```python
# FASE 2: Get scored signal
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.scoring_engine import ScoringEngine, TradeDirection

mtf = MultiTimeframeLayer()
scorer = ScoringEngine()

mtf_data = mtf.get_multi_timeframe_data("SPY")
signal = scorer.score_signal(mtf_data, TradeDirection.LONG)

# FASE 3: Use signal in multiple ways
from tradingagents.dataflows.backtester import Backtester
from tradingagents.dataflows.report_generator import ReportGenerator
from tradingagents.dataflows.alert_system import AlertSystem, AlertConfig

# Backtest historical signals
backtester = Backtester()
result = backtester.run_backtest("SPY", start_date, end_date)

# Generate report
generator = ReportGenerator()
generator.generate_screener_report(["SPY", "QQQ"], "report.html")

# Send alert if strong
if signal.total_score >= 75.0:
    alert_system = AlertSystem(AlertConfig())
    alert_system.send_signal_alert(signal, "Strong setup detected")
```

---

## Testing

**File**: `test_fase3_infrastructure.py` (400 lines)

### Test Coverage

1. **Trade Class**: P&L calculation for LONG/SHORT
2. **BacktestResult**: Metrics computation
3. **Backtester**: Historical simulation
4. **Report Generator**: HTML generation
5. **Alert Configuration**: Env vars and explicit config
6. **Alert System**: Discord/Email formatting
7. **Full Integration**: Complete workflow

### Running Tests

```bash
# Run all tests
python test_fase3_infrastructure.py

# Expected output:
# ✅ Trade Class: PASSED
# ✅ BacktestResult: PASSED
# ✅ Backtester: PASSED
# ✅ Report Generator: PASSED
# ✅ Alert Configuration: PASSED
# ✅ Alert System: PASSED
# ✅ Full Integration: PASSED
```

---

## Production Workflows

See `tradingagents/dataflows/fase3_integration_examples.py` for complete examples:

### Workflow A: Daily Morning Scan
1. Scan watchlist (20-30 symbols)
2. Score all symbols
3. Filter strong signals (>= 75/100)
4. Generate HTML report
5. Send alerts for new signals

**Schedule**: 8:00 AM ET daily

### Workflow B: Backtest Validation
1. Run historical test (last 6-12 months)
2. Calculate performance metrics
3. Generate backtest report
4. Review before going live

**Schedule**: Before deploying new strategy

### Workflow C: Weekly Deep Dive
1. Scan expanded watchlist (50+ symbols)
2. Generate comprehensive report
3. Email summary to team
4. Plan week ahead

**Schedule**: Sunday evening

### Workflow D: Live Monitoring
1. Rescan watchlist every 60 minutes
2. Track score changes
3. Alert when signal crosses threshold
4. Rate limiting prevents spam

**Schedule**: During market hours (9:30 AM - 4:00 PM ET)

---

## Performance Optimization

### Caching

FASE 2 cache manager reduces API calls by ~50%:

```python
# Automatic caching
mtf_data = mtf.get_multi_timeframe_data("SPY")  # Cached 5 min

# Clear cache if needed
mtf.cache_manager.clear_cache("SPY")
```

### Batch Operations

Process multiple symbols efficiently:

```python
# Bad: Process one at a time
for symbol in watchlist:
    generate_report(symbol)  # Many separate reports

# Good: Process in batch
generate_screener_report(watchlist, ...)  # Single report
```

### Rate Limiting

Respect API limits:
- Alpha Vantage: 5 calls/min (free), 75 calls/min (premium)
- yfinance: No official limit, ~2000 calls/hour reasonable

```python
import time

for symbol in large_watchlist:
    try:
        mtf_data = mtf.get_multi_timeframe_data(symbol)
    except Exception as e:
        if "rate limit" in str(e).lower():
            print("Rate limited, waiting 60 seconds...")
            time.sleep(60)
```

---

## Dependencies

### Required Packages

```bash
pip install requests plotly pandas numpy yfinance alpha_vantage
```

### Environment Setup

```bash
# Alert configuration
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export EMAIL_FROM="your@email.com"
export EMAIL_PASSWORD="app_specific_password"
export EMAIL_TO="recipient@email.com"

# Data sources
export ALPHA_VANTAGE_API_KEY="your_key"
```

---

## Troubleshooting

### Backtester Issues

**Problem**: No trades generated
```python
# Check signal scores
result = backtester.run_backtest(...)
print(f"Trades: {result.total_trades}")

# Lower threshold if needed
backtester = Backtester(min_signal_score=60.0)  # Was 70.0
```

**Problem**: Unrealistic results
```python
# Check for lookahead bias
# Backtester uses walk-forward simulation - should be OK

# Verify stop/target placement
for trade in result.trades:
    print(f"{trade.symbol}: Entry={trade.entry_price}, Stop={trade.stop_loss}, Target={trade.take_profit}")
```

### Report Generation Issues

**Problem**: Charts not displaying
```python
# Ensure Plotly installed
pip install plotly

# Check browser console for JS errors
# Open report.html in browser, press F12
```

**Problem**: Report too large (> 50MB)
```python
# Reduce data points in charts
# In report_generator.py:
df_plot = daily_df.tail(60)  # Only last 60 days (was 100)
```

### Alert Issues

**Problem**: Discord alerts not sending
```python
# Verify webhook URL
config = AlertConfig(discord_webhook_url="https://discord.com/api/webhooks/...")
print(f"Discord enabled: {config.is_discord_enabled()}")

# Test webhook manually
import requests
requests.post(webhook_url, json={"content": "Test message"})
```

**Problem**: Email authentication failure
```python
# Gmail requires app password (not account password)
# 1. Go to myaccount.google.com/apppasswords
# 2. Generate app password
# 3. Use that in EMAIL_PASSWORD

# For other providers:
config = AlertConfig(
    smtp_server="smtp.office365.com",  # Outlook
    smtp_port=587,
    email_from="...",
    email_password="..."
)
```

**Problem**: Rate limiting too aggressive
```python
# Adjust rate limit window
# In alert_system.py:
if datetime.now() - last_alert < timedelta(hours=1):  # Change to 0.5 for 30 min
```

---

## Next Steps

FASE 3 infrastructure complete. Ready for:

1. **Production Deployment**:
   - Schedule daily scans (cron/Windows Task Scheduler)
   - Set up alert channels
   - Monitor performance

2. **FASE 4 Planning** (Future):
   - Trade execution integration (broker API)
   - Portfolio management
   - Position sizing
   - Risk management enforcement

3. **Enhancements**:
   - Machine learning score optimization
   - Additional chart patterns
   - Sentiment analysis integration
   - Performance dashboard

---

## Appendix: File Summary

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `backtester.py` | Historical testing | 580 | ✅ Complete |
| `report_generator.py` | HTML reports | 720 | ✅ Complete |
| `alert_system.py` | Notifications | 680 | ✅ Complete |
| `fase3_integration_examples.py` | Workflow examples | 500 | ✅ Complete |
| `test_fase3_infrastructure.py` | Test suite | 400 | ✅ Complete |
| `FASE3_ARCHITECTURE.md` | This document | 1,200 | ✅ Complete |

**Total**: ~4,080 lines of code + documentation
