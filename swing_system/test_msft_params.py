#!/usr/bin/env python3
"""Test caricamento parametri MSFT"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from optimized_engine import load_ticker_params

params = load_ticker_params('MSFT', 'params')

print('✓ Params caricati per MSFT')
print(f'  Indicatori: {len(params.get("indicators", {}))} parametri')
print(f'  Segnali: {len(params.get("signals", {}))} parametri')
print(f'  Risk profiles: {list(params.get("risk_profiles", {}).keys())}')
print(f'  Signal scores: {params.get("signal_scores", {})}')
print(f'  Warmup: {params.get("warmup", 0)} barre')
print(f'  Default profile: {params.get("risk_profile_default", "N/A")}')
print()
print('Risk profile bilanciato:')
risk_bal = params.get('risk_profiles', {}).get('bilanciato', {})
for sig_type, risk_pct in risk_bal.items():
    print(f'  {sig_type}: {risk_pct}%')
