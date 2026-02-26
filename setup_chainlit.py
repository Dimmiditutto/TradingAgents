#!/usr/bin/env python3
"""
Setup script per TradingAgents with Chainlit
Installa tutte le dipendenze necessarie
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, description, cwd="/workspaces/TradingAgents"):
    """Esegui un comando e stampa il risultato"""
    print(f"▶️  {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print(f"   ✅ {description} - OK")
            return True
        else:
            error = result.stderr.split('\n')[-2] if result.stderr else "Errore sconosciuto"
            print(f"   ⚠️  {error[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏱️  Timeout per {description}")
        return False
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False

def main():
    print("🚀 TradingAgents - Setup Chainlit")
    print("=" * 50)
    print()
    
    # Directory di lavoro
    base_dir = Path("/workspaces/TradingAgents")
    venv_path = base_dir / ".venv"
    
    # Step 1: Rimuovi venv vecchio se esiste
    if venv_path.exists():
        print("🗑️  Rimozione venv precedente...")
        shutil.rmtree(venv_path)
        print("   ✅ Rimosso\n")
    
    # Step 2: Crea nuovo venv
    print("📦 Creazione virtual environment...")
    run_command(
        "python3 -m venv .venv",
        "Python venv",
        cwd=str(base_dir)
    )
    print()
    
    # Determina il comando Python corretto
    if sys.platform == "win32":
        py_exe = str(venv_path / "Scripts" / "python.exe")
        pip_exe = str(venv_path / "Scripts" / "pip.exe")
    else:
        py_exe = str(venv_path / "bin" / "python")
        pip_exe = str(venv_path / "bin" / "pip")
    
    # Step 3: Upgrade pip
    print("📦 Aggiornamento pip...")
    run_command(
        f"{py_exe} -m pip install --upgrade pip setuptools wheel -q",
        "pip upgrade",
        cwd=str(base_dir)
    )
    print()
    
    # Step 4: Installa dipendenze critiche
    packages = [
        ("chainlit", "Chainlit"),
        ("langgraph", "LangGraph"),
        ("langchain-openai", "LangChain OpenAI"),
        ("langchain-anthropic", "LangChain Anthropic"),
        ("langchain-google-genai", "LangChain Google"),
        ("python-dotenv", "Python-dotenv"),
        ("pandas", "Pandas"),
        ("yfinance", "YFinance"),
        ("rich", "Rich"),
        ("questionary", "Questionary"),
    ]
    
    print("📦 Installazione dipendenze principali...")
    for pkg, desc in packages:
        run_command(
            f"{py_exe} -m pip install {pkg} -q",
            f"  Installazione {desc}",
            cwd=str(base_dir)
        )
    
    print()
    print("=" * 50)
    print("✅ Setup completato con successo!")
    print("=" * 50)
    print()
    print("🎯 Prossimi comandi:")
    print()
    
    if sys.platform == "win32":
        print(f"  1. Attiva il venv:")
        print(f"     .venv\\Scripts\\activate")
        print()
        print(f"  2. Vai nella cartella app:")
        print(f"     cd TradingAgents")
        print()
        print(f"  3. Avvia Chainlit:")
        print(f"     chainlit run app.py")
    else:
        print(f"  1. Attiva il venv:")
        print(f"     source .venv/bin/activate")
        print()
        print(f"  2. Vai nella cartella app:")
        print(f"     cd TradingAgents")
        print()
        print(f"  3. Avvia Chainlit:")
        print(f"     chainlit run app.py")
    
    print()
    print("📚 O direttamente con:")
    print(f"  {py_exe} -m chainlit run TradingAgents/app.py")
    print()

if __name__ == "__main__":
    main()
