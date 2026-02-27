"""
Example configuration using Alpha Vantage MCP for TradingAgents
Copy this to your main.py or use as a reference
"""

import os
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Create a custom config with MCP enabled
config = DEFAULT_CONFIG.copy()

# ========== LLM Configuration ==========
# Detect which LLM API key is available
openai_key = os.getenv("OPENAI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")

if openai_key:
    config["llm_provider"] = "openai"
    config["deep_think_llm"] = "gpt-5.2"
    config["quick_think_llm"] = "gpt-5-mini"
    print("✅ Using OpenAI LLM")
elif google_key:
    config["llm_provider"] = "google"
    config["deep_think_llm"] = "gemini-3.0-exp"
    config["quick_think_llm"] = "gemini-3.0-flash"
    print("✅ Using Google Gemini LLM")
elif anthropic_key:
    config["llm_provider"] = "anthropic"
    config["deep_think_llm"] = "claude-4-opus"
    config["quick_think_llm"] = "claude-4-sonnet"
    print("✅ Using Anthropic Claude LLM")
else:
    print("\n❌ ERROR: No LLM API key found!")
    print("\nSet one of these environment variables:")
    print("  export OPENAI_API_KEY=sk-...")
    print("  export GOOGLE_API_KEY=...")
    print("  export ANTHROPIC_API_KEY=...")
    print("\nThen run this script again.")
    exit(1)

# Check for Alpha Vantage API key
alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
if alpha_key:
    print(f"✅ Alpha Vantage API key found: {alpha_key[:8]}...{alpha_key[-4:]}")
else:
    print("⚠️  ALPHA_VANTAGE_API_KEY not set - will use yfinance as fallback")

# ========== Data Vendor Configuration ==========
# Use Alpha Vantage MCP for all financial data
if alpha_key:
    config["data_vendors"] = {
        "core_stock_apis": "mcp_alpha_vantage",       # Stock prices via MCP
        "technical_indicators": "mcp_alpha_vantage",  # Technical indicators via MCP
        "fundamental_data": "mcp_alpha_vantage",      # Company fundamentals via MCP
        "news_data": "mcp_alpha_vantage",             # News & sentiment via MCP
    }
    print("✅ Using Alpha Vantage MCP for data")
else:
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
    print("✅ Using yfinance for data")

# Or use a hybrid approach:
# config["data_vendors"] = {
#     "core_stock_apis": "mcp_alpha_vantage",       # MCP for stock data (faster)
#     "technical_indicators": "yfinance",           # yfinance for indicators (free)
#     "fundamental_data": "mcp_alpha_vantage",      # MCP for fundamentals (better quality)
#     "news_data": "yfinance",                      # yfinance for news (free)
# }

# Or override specific tools:
# config["tool_vendors"] = {
#     "get_stock_data": "mcp_alpha_vantage",  # Only stock data via MCP
#     "get_fundamentals": "yfinance",         # Rest use default from category
# }

# ========== Trading Configuration ==========
config["max_debate_rounds"] = 2              # Number of debate rounds
config["max_risk_discuss_rounds"] = 2        # Risk management discussion rounds

# ========== Initialize TradingAgents ==========
ta = TradingAgentsGraph(debug=True, config=config)

# ========== Run Analysis ==========
if __name__ == "__main__":
    import sys
    
    # Get ticker from command line or use default
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    date = sys.argv[2] if len(sys.argv) > 2 else "2026-01-15"
    
    print(f"\n{'='*60}")
    print(f"Running TradingAgents Analysis")
    print(f"Ticker: {ticker}")
    print(f"Date: {date}")
    print(f"Data Source: Alpha Vantage MCP")
    print(f"{'='*60}\n")
    
    try:
        # Forward propagate through the trading agents
        final_state, decision = ta.propagate(ticker, date)
        
        print(f"\n{'='*60}")
        print("Analysis Complete!")
        print(f"{'='*60}")
        print(f"\nFinal Decision:\n{decision}\n")
        
        # Optionally save results
        from tradingagents.utils.report_generator import ReportGenerator
        rep_gen = ReportGenerator()
        
        # Generate reports
        pdf_path, excel_path = rep_gen.generate_both_reports(
            ticker=ticker,
            date=date,
            decision=decision,
            analysis_data=final_state
        )
        
        print(f"Reports saved:")
        print(f"  PDF: {pdf_path}")
        print(f"  Excel: {excel_path}")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
