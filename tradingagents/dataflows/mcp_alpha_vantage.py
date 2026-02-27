"""
Alpha Vantage MCP (Model Context Protocol) Integration
Uses the official Alpha Vantage MCP server for standardized tool access.
Server: https://mcp.alphavantage.co/mcp
"""

import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

MCP_SERVER_URL = "https://mcp.alphavantage.co/mcp"

class MCPError(Exception):
    """Exception raised when MCP server returns an error."""
    pass

class MCPRateLimitError(MCPError):
    """Exception raised when MCP rate limit is exceeded."""
    pass

def get_mcp_api_key() -> str:
    """Retrieve the API key for Alpha Vantage MCP from environment variables."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise ValueError(
            "ALPHA_VANTAGE_API_KEY environment variable is not set. "
            "Get your free key at https://www.alphavantage.co/support/#api-key"
        )
    return api_key

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Call an Alpha Vantage MCP tool.
    
    Args:
        tool_name: Name of the MCP tool (e.g., "TIME_SERIES_DAILY", "RSI")
        arguments: Dictionary of arguments for the tool
        
    Returns:
        Tool response data
        
    Raises:
        MCPError: If the MCP server returns an error
        MCPRateLimitError: If rate limit is exceeded
    """
    api_key = get_mcp_api_key()
    
    # MCP request format - try different formats if needed
    payload = {
        "tool_name": tool_name,
        "arguments": arguments
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    
    # Add API key - try as Bearer token first, then as parameter
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        # Also add as query parameter for fallback
        url = f"{MCP_SERVER_URL}?apikey={api_key}"
    else:
        url = MCP_SERVER_URL
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Check for rate limit
        if response.status_code == 429:
            raise MCPRateLimitError(
                "Alpha Vantage MCP rate limit exceeded. "
                "Free tier: 25 requests/day. Upgrade at alphavantage.co"
            )
        
        # Accept 200 and 202 (Accepted) as success
        if response.status_code not in [200, 201, 202]:
            error_msg = response.text if response.text else f"HTTP {response.status_code}"
            # Print debug info
            import sys
            print(f"DEBUG: Status code {response.status_code}", file=sys.stderr)
            print(f"DEBUG: Response headers: {response.headers}", file=sys.stderr)
            print(f"DEBUG: Response body: {error_msg[:500]}", file=sys.stderr)
            raise MCPError(f"MCP server error: {error_msg}")
        
        # Try to parse JSON response
        try:
            data = response.json()
        except:
            # If no JSON, return the text
            data = response.text
        
        # Check for API-level errors in JSON response
        if isinstance(data, dict):
            if "error" in data:
                raise MCPError(f"MCP tool error: {data['error']}")
            if "Error Message" in data:
                raise MCPError(f"Alpha Vantage error: {data['Error Message']}")
            if "Note" in data and "API call frequency" in data["Note"]:
                raise MCPRateLimitError(data["Note"])
        
        return data
        
    except requests.exceptions.Timeout:
        raise MCPError("MCP server timeout after 30 seconds")
    except requests.exceptions.ConnectionError as e:
        raise MCPError(f"Cannot connect to MCP server: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise MCPError(f"Request failed: {str(e)}")

def list_mcp_tools() -> Dict[str, Any]:
    """
    Get list of available MCP tools from the server.
    
    Returns:
        Dictionary of tool names and their descriptions
    """
    try:
        return call_mcp_tool("TOOL_LIST", {})
    except Exception as e:
        print(f"Warning: Could not fetch MCP tool list: {e}")
        return {}

# ==================== STOCK DATA ====================

def get_stock(symbol: str, start_date: str, end_date: str) -> str:
    """
    Get daily OHLCV stock data via MCP.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        CSV string with daily stock data
    """
    # Parse dates to determine outputsize
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()
    days_from_today = (today - start_dt).days
    
    outputsize = "compact" if days_from_today < 100 else "full"
    
    result = call_mcp_tool(
        "TIME_SERIES_DAILY_ADJUSTED",
        {
            "symbol": symbol,
            "outputsize": outputsize,
            "datatype": "csv"
        }
    )
    
    # Filter by date range (MCP returns full dataset)
    return _filter_csv_by_date_range(result, start_date, end_date)

def _filter_csv_by_date_range(csv_data: str, start_date: str, end_date: str) -> str:
    """Filter CSV data by date range."""
    import pandas as pd
    from io import StringIO
    
    if not csv_data or not csv_data.strip():
        return ""
    
    try:
        df = pd.read_csv(StringIO(csv_data))
        
        # Assume first column is date (timestamp)
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Filter by date range
        mask = (df[date_col] >= start_date) & (df[date_col] <= end_date)
        filtered_df = df.loc[mask]
        
        return filtered_df.to_csv(index=False)
    except Exception as e:
        print(f"Warning: Could not filter CSV data: {e}")
        return csv_data

# ==================== TECHNICAL INDICATORS ====================

def get_indicator(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
    interval: str = "daily",
    time_period: int = 14,
    series_type: str = "close"
) -> str:
    """
    Get technical indicator data via MCP.
    
    Args:
        symbol: Stock ticker symbol
        indicator: Indicator name (e.g., "rsi", "macd", "boll")
        curr_date: Current date in YYYY-MM-DD format
        look_back_days: Number of days to look back
        interval: Time interval (daily, weekly, monthly)
        time_period: Period for indicator calculation
        series_type: Price type (close, open, high, low)
        
    Returns:
        Formatted string with indicator data
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    # Map internal indicator names to MCP tool names
    indicator_map = {
        "close_50_sma": ("SMA", 50),
        "close_200_sma": ("SMA", 200),
        "close_10_ema": ("EMA", 10),
        "macd": ("MACD", None),
        "rsi": ("RSI", 14),
        "boll": ("BBANDS", 20),
        "atr": ("ATR", 14),
    }
    
    if indicator not in indicator_map:
        raise ValueError(f"Indicator {indicator} not supported via MCP")
    
    tool_name, default_period = indicator_map[indicator]
    if default_period:
        time_period = default_period
    
    arguments = {
        "symbol": symbol,
        "interval": interval,
        "time_period": time_period,
        "series_type": series_type,
        "datatype": "csv"
    }
    
    result = call_mcp_tool(tool_name, arguments)
    
    # Format result for agents
    return f"Technical Indicator: {indicator}\nSymbol: {symbol}\nData:\n{result}"

# ==================== FUNDAMENTAL DATA ====================

def get_fundamentals(symbol: str) -> str:
    """Get company overview and fundamental data via MCP."""
    result = call_mcp_tool(
        "OVERVIEW",
        {"symbol": symbol}
    )
    
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)

def get_balance_sheet(symbol: str) -> str:
    """Get company balance sheet via MCP."""
    result = call_mcp_tool(
        "BALANCE_SHEET",
        {"symbol": symbol}
    )
    
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)

def get_cashflow(symbol: str) -> str:
    """Get company cash flow statement via MCP."""
    result = call_mcp_tool(
        "CASH_FLOW",
        {"symbol": symbol}
    )
    
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)

def get_income_statement(symbol: str) -> str:
    """Get company income statement via MCP."""
    result = call_mcp_tool(
        "INCOME_STATEMENT",
        {"symbol": symbol}
    )
    
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)

# ==================== NEWS DATA ====================

def get_news(
    symbol: Optional[str] = None,
    topics: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    limit: int = 50
) -> str:
    """Get news and sentiment data via MCP."""
    arguments = {"limit": limit}
    
    if symbol:
        arguments["tickers"] = symbol
    if topics:
        arguments["topics"] = topics
    if time_from:
        arguments["time_from"] = time_from
    if time_to:
        arguments["time_to"] = time_to
    
    result = call_mcp_tool("NEWS_SENTIMENT", arguments)
    
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)

def get_global_news(topics: Optional[str] = None, limit: int = 50) -> str:
    """Get global market news via MCP."""
    return get_news(symbol=None, topics=topics, limit=limit)

def get_insider_transactions(symbol: str) -> str:
    """
    Get insider transactions via MCP.
    Note: This may require a premium Alpha Vantage subscription.
    """
    try:
        result = call_mcp_tool(
            "INSIDER_TRANSACTIONS",
            {"symbol": symbol}
        )
        
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except MCPError as e:
        return f"Insider transactions not available: {str(e)}"
