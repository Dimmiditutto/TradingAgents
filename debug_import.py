#!/usr/bin/env python
"""
Debug script per verificare l'import di TradingAgentsGraph
Eseguilo per vedere esattamente cosa sta fallendo
"""
import sys
import os

# Setup path come fa app.py
from pathlib import Path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# IMPORTANTE: Carica .env prima di tutto
from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("DEBUG: TradingAgentsGraph Import Test")
print("="*70)
print(f"\nPython path:")
for p in sys.path[:3]:
    print(f"  - {p}")

# Check API keys
print(f"\nAPI Keys check:")
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    print(f"  ✅ OPENAI_API_KEY: {openai_key[:20]}...{openai_key[-10:]}")
else:
    print(f"  ❌ OPENAI_API_KEY: NOT SET")
    
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key:
    print(f"  ✅ ANTHROPIC_API_KEY: {anthropic_key[:20]}...{anthropic_key[-10:]}")
else:
    print(f"  ⚠️ ANTHROPIC_API_KEY: NOT SET (optional)")

google_key = os.getenv("GOOGLE_API_KEY")
if google_key:
    print(f"  ✅ GOOGLE_API_KEY: {google_key[:20]}...{google_key[-10:]}")
else:
    print(f"  ⚠️ GOOGLE_API_KEY: NOT SET (optional)")

print(f"\nWorking directory: {os.getcwd()}")
print(f"Parent directory: {parent_dir}")

# Test 1: Import tradingagents package
print("\n" + "-"*70)
print("Test 1: Import tradingagents package")
print("-"*70)
try:
    import tradingagents
    print(f"✅ tradingagents package found at: {tradingagents.__file__}")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Import default_config
print("\n" + "-"*70)
print("Test 2: Import default_config")
print("-"*70)
try:
    from tradingagents.default_config import DEFAULT_CONFIG
    print(f"✅ DEFAULT_CONFIG loaded")
    print(f"   Keys: {list(DEFAULT_CONFIG.keys())[:5]}...")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Import graph package
print("\n" + "-"*70)
print("Test 3: Import graph package")
print("-"*70)
try:
    from tradingagents import graph
    print(f"✅ graph package found at: {graph.__file__}")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Import TradingAgentsGraph class
print("\n" + "-"*70)
print("Test 4: Import TradingAgentsGraph class")
print("-"*70)
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    print(f"✅ TradingAgentsGraph imported")
    print(f"   Type: {type(TradingAgentsGraph)}")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Create instance
print("\n" + "-"*70)
print("Test 5: Create TradingAgentsGraph instance")
print("-"*70)
try:
    config = DEFAULT_CONFIG.copy()
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
    
    print("Creating instance (this may take 10-20 seconds)...")
    ta = TradingAgentsGraph(debug=False, config=config)
    print(f"✅ TradingAgentsGraph instance created")
    print(f"   Type: {type(ta)}")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("✅✅✅ ALL TESTS PASSED ✅✅✅")
print("="*70)
print("\nTradingAgentsGraph can be imported and instantiated successfully.")
print("The issue might be environment-specific (async context, etc.)")
