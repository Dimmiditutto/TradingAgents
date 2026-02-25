# TradingAgents Web App

**Sistema di Analisi Trading Automatico con Interfaccia Web Interattiva**

Applicazione completa per analizzare titoli finanziari usando un sistema multi-agente AI con:
- 🎯 Dashboard interattivo con grafici in tempo reale
- 📊 Report scaricabili in PDF e Excel
- 🤖 Analisi multi-agente con Bull/Bear/Risk Managers
- 💬 Interfaccia chat moderna e intuitiva in italiano

## 🚀 Quick Start Locale

### 1. Installa Dipendenze

```bash
cd /workspaces/TradingAgents/TradingAgents

# Se non hai ancora creato l'ambiente virtuale:
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze base
pip install -r requirements.txt

# Installa dipendenze aggiuntive per web, report e grafici
pip install reportlab openpyxl plotly kaleido
```

### 2. Configura Variabili d'Ambiente

```bash
# Nel terminale:
export OPENAI_API_KEY=sk_your_key_here
export ALPHA_VANTAGE_API_KEY=your_api_key_here
```

Oppure crea un file `.env`:
```
OPENAI_API_KEY=sk_your_key_here
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

### 3. Lancia l'App

```bash
# Attiva l'ambiente
source venv/bin/activate

# Lancia Chainlit
chainlit run app.py

# Accedi a http://localhost:8000
```

## 📋 File di Configurazione

### requirements.txt
```
typing-extensions
langchain-core
langchain-openai
langchain-experimental
pandas
yfinance
stockstats
langgraph
rank-bm25
setuptools
backtrader
parsel
requests
tqdm
pytz
redis
chainlit
rich
typer
questionary
reportlab
openpyxl
plotly
kaleido
```

## 🌐 Deploy su Render

### Step 1: Prepara il Repository

1. Crea un repository GitHub con questi file:
   - `app.py`
   - `requirements.txt`
   - `tradingagents/` (intero folder)
   - `.env.example` (template per le variabili)

### Step 2: Crea l'App su Render

1. Vai su [render.com](https://render.com)
2. Clicca "New +" → "Web Service"
3. Collega il tuo repository GitHub
4. Configura:
   - **Name**: `trading-agents-app`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `chainlit run app.py`
   - **instance Type**: Standard (3.5GB RAM minimo)

### Step 3: Aggiungi Variabili d'Ambiente

Nel dashboard Render, aggiungi in "Environment":

```
OPENAI_API_KEY=sk_your_actual_key
ALPHA_VANTAGE_API_KEY=your_actual_key
```

### Step 4: Deploy

Clicca "Create Web Service" e Render farà il deploy automatico!

L'app sarà disponibile a: `https://trading-agents-app.onrender.com`

## 📁 Struttura File

```
app.py                                      # App principale Chainlit
requirements.txt                            # Dipendenze
tradingagents/
├── utils/
│   ├── report_generator.py                # Generatore PDF/Excel ✨
│   ├── dashboard.py                        # Dashboard Plotly ✨
│   └── ... (altri file)
├── graph/
│   ├── trading_graph.py                   # Engine principale
│   └── ... (altre componenti)
└── agents/
    ├── analysts/                           # Analisti
    ├── researchers/                        # Ricercatori
    ├── managers/                           # Manager
    └── ... (altri agenti)
```

## 💡 Come Usare l'App

### Comandi Disponibili

```
ANALIZZA NVDA                    # Analizza NVIDIA (data attuale)
ANALIZZA AAPL 2024-05-10        # Analizza Apple per data specifica
LISTA                            # Vedi asset disponibili
AIUTO                            # Mostra guida completa
```

### Output Ricevuti

Per ogni analisi ottieni:

1. **Decisione Trading**
   - 💚 ACQUISTO (score positivo)
   - ❌ VENDITA (score negativo)
   - ⏳ ATTESA (score ~0)

2. **Dashboard HTML Interattivo**
   - Gauge della decisione
   - Pie chart consensus
   - Grafici dei prezzi
   - Radar chart agenti

3. **Report PDF Formale**
   - Analisi completa
   - Dati strutturati
   - Pronto per stampa

4. **Foglio Excel**
   - Dati strutturati
   - Facilmente modificabile
   - Pronto per ulteriori analisi

## 🔧 Personalizzazione

### Cambia Modello LLM

Modifica in `app.py`:

```python
config["deep_think_llm"] = "gpt-4"      # Model principale
config["quick_think_llm"] = "gpt-3.5"   # Model veloce
```

### Cambia Fonte Dati

In `app.py`:

```python
config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",     # o "yfinance"
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}
```

### Personalizza Dashboard

Modifica `tradingagents/utils/dashboard.py`:
- Colori in `create_decision_gauge()`
- Layout in `create_dashboard_html()`
- Metriche in `create_performance_table()`

## 🛡️ Note di Sicurezza

⚠️ **IMPORTANTE:**
- Non commitare file `.env` con credenziali reali
- Usa Render's environment variables per credenziali in produzione
- Le API keys sono sensibili - proteggi il tuo repository

## 📊 Monitoraggio

### Log su Render

Nel dashboard Render, accedi a "Logs" per debuggare l'app in produzione

### Report Generati

I report e dashboard vengono salvati in:
- `./reports/` - PDF e Excel
- `./dashboards/` - HTML interattivi

## 🐛 Troubleshooting

### "ModuleNotFoundError: chainlit"
```bash
pip install chainlit
```

### "OPENAI_API_KEY not found"
```bash
export OPENAI_API_KEY=sk_your_key
# o aggiungi a .env
```

### Deploy su Render fallisce
- Assicurati che `requirements.txt` sia aggiornato
- Verifica che Python3 sia configurato correttamente
- Aumenta RAM allocata (Standard minimo 3.5GB)

### App lenta
- Primo caricamento richiede 10-15 secondi
- Utilizza yfinance per dati più veloci
- Disabilita `debug=True` in `app.py`

## 📚 Risorse

- [Chainlit Docs](https://docs.chainlit.io)
- [Render Docs](https://render.com/docs)
- [yFinance Docs](https://yfinance.readthedocs.io)
- [Plotly Docs](https://plotly.com/python/)

## 📝 Licenza

Vedi [LICENSE](../LICENSE)

## 👨‍💻 Contribuire

Vuoi contribuire? Perfetto!

1. Fai un Fork
2. Crea branch feature: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Apri Pull Request

## 📞 Supporto

Per problemi o domande:
- 📧 Apri un Issue
- 💬 Discussioni nel repository
- 🔗 Controlla i Logs di Render

---

**Fatto con ❤️ da TradingAgents Team**

Ricorda: questo è uno strumento di analisi. Sempre consulta esperti prima di fare trading! 📊
