# Alpha Vantage MCP Integration

TradingAgents now supports **Alpha Vantage via MCP (Model Context Protocol)** for enhanced financial data access.

## 🚀 What is MCP?

MCP (Model Context Protocol) is a standardized way for AI agents to access external tools and data sources. Alpha Vantage's MCP server provides:

✅ **Standardized interface** - Works seamlessly with all LLM providers (OpenAI, Anthropic, Google)
✅ **Automatic rate limiting** - Server-managed request throttling
✅ **Built-in caching** - Faster repeated queries
✅ **Better error handling** - Graceful degradation and retry logic
✅ **Direct tool access** - LLMs can call Alpha Vantage functions directly

## 📝 Setup Instructions

### 1. Get Your Alpha Vantage API Key

Visit: https://www.alphavantage.co/support/#api-key

- **Free tier**: 25 requests per day
- **Paid tiers**: Higher rate limits

### 2. Add API Key to Environment

Edit your `.env` file:

```bash
# Alpha Vantage API Key (used by both REST API and MCP)
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

### 3. Configure TradingAgents to Use MCP

Edit `tradingagents/default_config.py` or your custom config:

```python
"data_vendors": {
    "core_stock_apis": "mcp_alpha_vantage",       # Use MCP for stock data
    "technical_indicators": "mcp_alpha_vantage",  # Use MCP for indicators
    "fundamental_data": "mcp_alpha_vantage",      # Use MCP for fundamentals
    "news_data": "mcp_alpha_vantage",             # Use MCP for news
}
```

Or override specific tools:

```python
"tool_vendors": {
    "get_stock_data": "mcp_alpha_vantage",  # Only stock data via MCP
    "get_fundamentals": "yfinance",         # Fundamentals from yfinance
}
```

## 🔄 Connection Modes

### Remote Server (Recommended)

**URL**: `https://mcp.alphavantage.co/mcp`

**Pros:**
- Zero local setup
- Always up-to-date
- Professional rate limiting
- High availability

**Cons:**
- Network latency (~50-100ms)
- Requires internet connection

This is the **default mode** used by TradingAgents.

### Local Server (Advanced)

Install the MCP server locally:

```bash
# Install uvx if not already available
pip install uvx

# Run local MCP server
uvx av-mcp YOUR_API_KEY
```

Then update `mcp_alpha_vantage.py`:

```python
MCP_SERVER_URL = "http://localhost:8080/mcp"  # Adjust port as needed
```

## 🎯 Usage Examples

### In TradingAgents

Once configured, everything works automatically:

```bash
# CLI
python main.py AAPL

# Web interface
ANALIZZA AAPL
```

The system will automatically use MCP for Alpha Vantage data.

### Direct MCP Usage (Python)

```python
from tradingagents.dataflows.mcp_alpha_vantage import call_mcp_tool

# Get stock data
data = call_mcp_tool(
    "TIME_SERIES_DAILY",
    {"symbol": "AAPL", "outputsize": "compact"}
)

# Get technical indicator
rsi = call_mcp_tool(
    "RSI",
    {"symbol": "AAPL", "interval": "daily", "time_period": 14}
)

# Get company overview
overview = call_mcp_tool(
    "OVERVIEW",
    {"symbol": "AAPL"}
)

# Get news sentiment
news = call_mcp_tool(
    "NEWS_SENTIMENT",
    {"tickers": "AAPL", "limit": 50}
)
```

## 🔧 Available MCP Tools

Alpha Vantage MCP server provides these tools:

### Stock Data
- `TIME_SERIES_DAILY` - Daily OHLCV data
- `TIME_SERIES_DAILY_ADJUSTED` - Adjusted for splits/dividends
- `TIME_SERIES_INTRADAY` - Intraday data (1min, 5min, etc.)

### Technical Indicators
- `SMA` - Simple Moving Average
- `EMA` - Exponential Moving Average
- `RSI` - Relative Strength Index
- `MACD` - Moving Average Convergence Divergence
- `BBANDS` - Bollinger Bands
- `ATR` - Average True Range
- `STOCH` - Stochastic Oscillator
- `ADX` - Average Directional Index

### Fundamental Data
- `OVERVIEW` - Company overview
- `BALANCE_SHEET` - Balance sheet
- `INCOME_STATEMENT` - Income statement
- `CASH_FLOW` - Cash flow statement
- `EARNINGS` - Quarterly/annual earnings

### News & Sentiment
- `NEWS_SENTIMENT` - News with sentiment analysis
- `TOP_GAINERS_LOSERS` - Market movers

### Economic Data
- `REAL_GDP` - GDP data
- `INFLATION` - Inflation rates
- `UNEMPLOYMENT` - Unemployment rates

## 🛡️ Error Handling

The MCP integration includes robust error handling:

```python
from tradingagents.dataflows.mcp_alpha_vantage import MCPError, MCPRateLimitError

try:
    data = call_mcp_tool("TIME_SERIES_DAILY", {"symbol": "AAPL"})
except MCPRateLimitError as e:
    print("Rate limit exceeded:", e)
    # Fall back to yfinance or wait
except MCPError as e:
    print("MCP error:", e)
    # Handle other errors
```

## 🔀 Vendor Priority & Fallback

TradingAgents automatically falls back to alternative vendors if MCP fails:

**Priority order:**
1. `mcp_alpha_vantage` (if configured)
2. `alpha_vantage` (REST API)
3. `yfinance` (free, no API key needed)

This ensures your analyses always complete, even if one data source is unavailable.

## 📊 Performance Comparison

| Feature | yfinance | alpha_vantage (REST) | mcp_alpha_vantage |
|---------|----------|---------------------|-------------------|
| **Latency** | 200-500ms | 300-600ms | 100-300ms (with cache) |
| **Rate Limiting** | None | Client-side | Server-managed |
| **Caching** | None | Local file cache | Server-side cache |
| **Cost** | Free | Free tier limited | Same as REST API |
| **Reliability** | High | Medium | High |
| **Setup** | None | API key only | API key only |

## 🔍 Troubleshooting

### "Cannot connect to MCP server"
- Check your internet connection
- Verify the MCP server URL is correct
- Try the local server option

### "Rate limit exceeded"
- You've hit the 25 requests/day limit on free tier
- Consider upgrading your Alpha Vantage plan
- System will automatically fall back to yfinance

### "API key invalid"
- Check your `.env` file has the correct key
- Verify the key is active at alphavantage.co
- Make sure there are no extra spaces

### Import errors
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Install any missing dependencies
pip install requests python-dateutil pandas
```

## 🌐 OpenAI Agent Builder Integration

If you're using OpenAI's Agent Builder, you can connect it directly to Alpha Vantage MCP:

1. Open your agent in Agent Builder
2. Go to **Tools** → **+ Add Tool**
3. Select **MCP Server**
4. Configure:
   - **URL**: `https://mcp.alphavantage.co/mcp`
   - **Label**: Alpha Vantage MCP Server
   - **Authentication**: Access token / API key
   - **Access Token**: Your Alpha Vantage API key
5. Click **Connect** and **Add**

Your agent can now call Alpha Vantage tools directly!

## 📚 Additional Resources

- **Alpha Vantage MCP GitHub**: https://github.com/alphavantage/alpha_vantage_mcp
- **Alpha Vantage Documentation**: https://www.alphavantage.co/documentation/
- **MCP Specification**: https://modelcontextprotocol.io/
- **TradingAgents Docs**: README.md

## 🆘 Support

For issues with:
- **MCP integration in TradingAgents**: Open an issue on GitHub
- **Alpha Vantage API**: Contact support@alphavantage.co
- **MCP server**: https://github.com/alphavantage/alpha_vantage_mcp/issues

---

**Last updated**: February 2026
**TradingAgents version**: 1.x
**MCP Protocol version**: 1.0
