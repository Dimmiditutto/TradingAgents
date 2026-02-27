#!/usr/bin/env python3
"""
Simple Chainlit starter for GitHub Codespaces
"""
import subprocess
import sys
import os
import time

# Set environment
os.chdir("/workspaces/TradingAgents/web")
os.environ["PYTHONUNBUFFERED"] = "1"

# Kill any existing processes
print("🔴 Killing existing Chainlit processes...")
os.system("pkill -9 -f 'chainlit run' 2>/dev/null")
time.sleep(2)

# Start Chainlit
print("🚀 Starting Chainlit...")
print("=" * 70)

cmd = [
    sys.executable, "-m", "chainlit", "run",
    "app.py",
    "--host", "0.0.0.0",
    "--port", "8000"
]

print(f"Command: {' '.join(cmd)}")
print("=" * 70)
print()

try:
    subprocess.run(cmd, check=False)
except KeyboardInterrupt:
    print("\n\n🛑 Stopped")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
