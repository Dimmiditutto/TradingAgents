#!/usr/bin/env python
"""Quick test - just check if imports work"""
import sys
import os
from pathlib import Path

# Setup path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Load env
from dotenv import load_dotenv
load_dotenv()

print("Quick Import Test")
print("="*70)

# Check API key
openai_key = os.getenv("OPENAI_API_KEY")
print(f"✅ API Key: {openai_key[:20]}..." if openai_key else "❌ No API key")

# Test imports
try:
    from tradingagents.default_config import DEFAULT_CONFIG
    print("✅ DEFAULT_CONFIG imported")
    
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    print("✅ TradingAgentsGraph class imported")
    
    print("\n" + "="*70)
    print("✅ ALL IMPORTS SUCCESSFUL")
    print("="*70)
    print("\nTradingAgentsGraph CAN be loaded.")
    print("The issue in the web app might be:")
    print("1. Different working directory")
    print("2. .env not loaded in the right order")
    print("3. Async context issues")
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
