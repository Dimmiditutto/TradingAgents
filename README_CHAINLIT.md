# 🚀 TradingAgents - Chainlit Web App

## Nuova Struttura

La cartella è stata rinominata per chiarezza:
- **`/workspaces/TradingAgents/web/`** ← Chainlit app (era `TradingAgents/`)
- **`/workspaces/TradingAgents/tradingagents/`** ← Moduli AI
- **`/workspaces/TradingAgents/cli/`** ← CLI originale

## Come Avviare

### Opzione 1: Script automatico
```bash
cd /workspaces/TradingAgents
bash run_app.sh
```

### Opzione 2: Manuale
```bash
cd /workspaces/TradingAgents/web
/workspaces/TradingAgents/.venv/bin/python -m chainlit run app.py
```

### Opzione 3: Con venv attivo
```bash
cd /workspaces/TradingAgents
source .venv/bin/activate
cd web
chainlit run app.py
```

## 🌐 Accedere all'App

Apri nel browser:
```
http://localhost:8000
```

## 💬 Primo Comando

Nella chat scrivi:
```
CONFIGURA
```

E segui il wizard interattivo! 

## 📋 Comandi Disponibili

| Comando | Descrizione |
|---------|------------|
| `CONFIGURA` | Setup guidato con selezione parametri |
| `ANALIZZA <TICKER>` | Analizza un titolo con tuoi parametri |
| `ANALIZZA <TICKER> <DATA>` | Analizza per data specifica |
| `LISTA` | Mostra asset supportati |
| `AIUTO` | Guida completa |

## 📚 File Importanti

- **`app.py`** - App principale Chainlit
- **`chainlit_config.py`** - Configurazione interattiva
- **`../tradingagents/`** - Moduli AI
- **`../tradingagents/utils/`** - Report e Dashboard generators

## 🔧 Configurazione

Le API keys vanno in `.env`:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```

## 📊 Output

Ogni analisi genera:
- 📊 Dashboard HTML interattivo
- 📄 Report PDF
- 📋 Dati Excel

## ✅ Tutto Funziona!

La struttura è ora pulita e non ci sono conflitti. Buona analisi! 🎯
