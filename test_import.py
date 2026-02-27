#!/usr/bin/env python
"""Test TradingAgentsGraph import"""
import sys
sys.path.insert(0, "/workspaces/TradingAgents")

print("Testing TradingAgentsGraph import...")
print("="*70)

try:
    print("1. Loading default_config...")
    from tradingagents.default_config import DEFAULT_CONFIG
    print("   ✅ DEFAULT_CONFIG loaded")
    
    print("\n2. Loading TradingAgentsGraph...")
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    print("   ✅ TradingAgentsGraph imported")
    
    print("\n3. Creating instance...")
    config = DEFAULT_CONFIG.copy()
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
    
    ta = TradingAgentsGraph(debug=False, config=config)
    print("   ✅ TradingAgentsGraph instantiated")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    
except Exception as e:
    import traceback
    print("\n" + "="*70)
    print("❌ ERROR")
    print("="*70)
    print(f"\nError: {e}")
    print("\nFull traceback:")
    print(traceback.format_exc())
