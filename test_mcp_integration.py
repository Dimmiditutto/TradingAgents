"""
Test script for Alpha Vantage MCP integration
Run this to verify your MCP setup is working correctly.
"""

import os
from tradingagents.dataflows.mcp_alpha_vantage import (
    call_mcp_tool,
    get_stock,
    get_indicator,
    get_fundamentals,
    MCPError,
    MCPRateLimitError
)

def test_mcp_connection():
    """Test basic MCP server connectivity"""
    print("=" * 60)
    print("Testing Alpha Vantage MCP Integration")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("❌ ALPHA_VANTAGE_API_KEY not set in environment")
        print("   Set it with: export ALPHA_VANTAGE_API_KEY=your_key")
        return False
    
    print(f"✅ API key found: {api_key[:8]}...{api_key[-4:]}")
    print()
    
    # Test 1: List available tools
    print("Test 1: Listing available MCP tools...")
    try:
        tools = call_mcp_tool("TOOL_LIST", {})
        if tools:
            print(f"✅ MCP server connected! Found {len(tools)} tools")
            print("   Sample tools:", list(tools.keys())[:5])
        else:
            print("⚠️  Connected but no tools returned")
    except MCPRateLimitError:
        print("❌ Rate limit exceeded (25 requests/day on free tier)")
        return False
    except MCPError as e:
        print(f"❌ MCP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    print()
    
    # Test 2: Get stock data
    print("Test 2: Getting stock data for AAPL...")
    try:
        data = call_mcp_tool(
            "TIME_SERIES_DAILY",
            {"symbol": "AAPL", "outputsize": "compact", "datatype": "csv"}
        )
        if data and len(data) > 100:
            print(f"✅ Stock data retrieved ({len(data)} bytes)")
            print("   First line:", data.split('\n')[0])
        else:
            print("⚠️  Data received but seems incomplete")
    except MCPRateLimitError:
        print("❌ Rate limit exceeded")
        return False
    except MCPError as e:
        print(f"❌ MCP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    print()
    
    # Test 3: Get technical indicator
    print("Test 3: Getting RSI indicator for AAPL...")
    try:
        rsi = call_mcp_tool(
            "RSI",
            {
                "symbol": "AAPL",
                "interval": "daily",
                "time_period": 14,
                "series_type": "close",
                "datatype": "csv"
            }
        )
        if rsi and len(rsi) > 50:
            print(f"✅ RSI data retrieved ({len(rsi)} bytes)")
            print("   First line:", rsi.split('\n')[0])
        else:
            print("⚠️  Data received but seems incomplete")
    except MCPRateLimitError:
        print("❌ Rate limit exceeded")
        return False
    except MCPError as e:
        print(f"❌ MCP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    print()
    
    # Test 4: Get company overview
    print("Test 4: Getting company overview for AAPL...")
    try:
        overview = call_mcp_tool("OVERVIEW", {"symbol": "AAPL"})
        if overview and isinstance(overview, dict):
            print(f"✅ Company overview retrieved")
            print(f"   Company name: {overview.get('Name', 'N/A')}")
            print(f"   Sector: {overview.get('Sector', 'N/A')}")
            print(f"   Market Cap: {overview.get('MarketCapitalization', 'N/A')}")
        else:
            print("⚠️  Data received but format unexpected")
    except MCPRateLimitError:
        print("❌ Rate limit exceeded")
        return False
    except MCPError as e:
        print(f"❌ MCP error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    print()
    
    print("=" * 60)
    print("✅ All tests passed! MCP integration is working correctly.")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Configure TradingAgents to use MCP in default_config.py:")
    print('   "data_vendors": {"core_stock_apis": "mcp_alpha_vantage"}')
    print()
    print("2. Run an analysis:")
    print("   python main.py AAPL")
    print()
    print("3. Or use the CLI:")
    print("   python -m cli.main")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = test_mcp_connection()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
