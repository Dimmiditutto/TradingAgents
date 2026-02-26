# 🎯 Setup Guidato Chainlit - Guida Rapida

## Cos'è di Nuovo?

Ora puoi configurare TradingAgents direttamente da **Chainlit** con un'interfaccia interattiva passo-dopo-passo, esattamente come nella CLI!

## Come Iniziare (3 Passi)

### 1️⃣ Accedi a Chainlit
```bash
chainlit run app.py
```

### 2️⃣ Digita `CONFIGURA`
Nella chat scrivi:
```
CONFIGURA
```

### 3️⃣ Rispondi alle Domande
- Scegli il **ticker** (es. NVDA)
- Inserisci la **data** dell'analisi
- Seleziona gli **analisti** che vuoi
- Scegli la **profondità della ricerca**
- Configura il **provider LLM**
- Seleziona i **modelli di thinking**

## Comandi

| Comando | Uso |
|---------|-----|
| `CONFIGURA` | ⭐ Setup guidato (CONSIGLIATO PRIMA!) |
| `ANALIZZA NVDA` | Analizza NVDA con i tuoi parametri |
| `ANALIZZA AAPL 2024-05-10` | Analizza AAPL per una data specifica |
| `LISTA` | Mostra asset supportati |
| `AIUTO` | Guida completa |

## Flusso Tipico

```
1. Digita: CONFIGURA
   ↓
2. Rispondi al wizard di configurazione
   ↓
3. App: "Configuration saved!"
   ↓
4. Digita: ANALIZZA NVDA
   ↓
5. Ricevi analisi completa + file CSV/PDF
```

## Cosa Puoi Configurare?

### 📊 Ticker & Data
- Quale titolo analizzare
- Data dell'analisi (opzionale)

### 👥 Team di Analisti
Scegli uno o più:
- 📈 Market Analyst (analisi tecnica)
- 🌐 Social Media Analyst (sentiment)
- 📰 News Analyst (notizie)
- 💼 Fundamentals Analyst (fondamentali)

### 🔍 Profondità Ricerca
- 🚀 **Shallow** - Veloce, 1 round
- ⚙️ **Medium** - Bilanciato, 3 rounds
- 🔬 **Deep** - Approfondito, 5 rounds

### 🤖 Provider LLM
- OpenAI (GPT-4)
- Anthropic (Claude)
- Google Gemini
- OpenRouter
- Ollama (locale)

### 🧠 Modelli di Thinking
- **Quick**: per decisioniveloci
- **Deep**: per analisi approfondita

## Esempio Passo-Passo

```
Tu:     CONFIGURA
App:    📊 Step 1: Ticker Symbol?
Tu:     NVDA

App:    📅 Step 2: Analysis Date?
Tu:     2024-05-10

App:    👥 Step 3: Select Analysts?
        [per Matrix Analyst] ✅ Yes
        [per Other Analysts] ❌ No

App:    🔍 Step 4: Research Depth?
Tu:     [clicca "Medium"]

App:    🤖 Step 5: LLM Provider?
Tu:     [clicca "OpenAI"]

App:    ⚡ Step 6a: Quick-Thinking?
Tu:     [seleziona GPT-4o-mini]

App:    🧠 Step 6b: Deep-Thinking?
Tu:     [seleziona GPT-4o]

App:    ✅ Configuration saved!

Tu:     ANALIZZA NVDA
App:    ⏳ Analyzing... [mostra progressi]
        ✅ Analysis complete! [scarica report]
```

## File Generati

Per ogni analisi riceverai:

📄 **Report PDF**
- Analisi formale completa
- Grafici e visualizzazioni

📊 **Dashboard HTML**
- Interfaccia interattiva
- Gauge decisione
- Breakdown sentiment

📋 **Dati Excel**
- Numeri strutturati
- Per analisi ulteriori

## Tips & Trucchi

💡 **Suggerimento 1: Primo Accesso**
```
CONFIGURA  ← fai questo prima!
```

💡 **Suggerimento 2: Analisi Rapida**
Se non vuoi configurare, puoi fare subito:
```
ANALIZZA SPY
```
(ma userà parametri di default)

💡 **Suggerimento 3: Cambiar Provider**
Se vuoi usare un diverso LLM:
```
CONFIGURA  ← digita di nuovo
```

💡 **Suggerimento 4: Migliori Risultati**
- Usa "Deep" se hai tempo
- Seleziona più analisti
- Usa dati di 6+ mesi

## Requisiti

Prima di usare, assicurati di avere:

```bash
# API Keys nel tuo .env file:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
# (dipende dal provider che usi)
```

## Supporto Provider

### OpenAI ✅
```
- gpt-4o (standard)
- gpt-4o-mini (veloce)
- o1 (ragionamento)
```

### Anthropic ✅
```
- claude-3-5-sonnet (consigliato)
- claude-3-5-haiku (veloce)
- claude-opus-4 (potente)
```

### Google ✅
```
- gemini-2.0-flash
- gemini-2.5-pro
```

### Ollama ✅
```
- llama3.1 (locale)
- qwen3 (locale)
```

## FAQ

**D: Posso cambiare i parametri dopo CONFIGURA?**
R: Sì, digita di nuovo `CONFIGURA`

**D: Cosa succede se non faccio CONFIGURA?**
R: Usi parametri di default, va bene comunque!

**D: Quanto tempo impiega un'analisi?**
R: Dipende dalla profondità:
- Shallow: ~1-2 minuti
- Medium: ~3-5 minuti
- Deep: ~5-10 minuti

**D: Posso analizzare criptovalute?**
R: Sì! Usa ticker come `BTC-USD`, `ETH-USD`

**D: Come leggo i risultati?**
- 🟢 Score positivo = **COMPRARE**
- 🔴 Score negativo = **VENDERE**
- ⚪ Score neutro = **ASPETTARE**

## Prossimi Passi

1. ✅ Avvia Chainlit: `chainlit run app.py`
2. ✅ Digita: `CONFIGURA`
3. ✅ Rispondi alle domande
4. ✅ Analizza: `ANALIZZA NVDA`
5. ✅ Scarica i risultati

Buona analisi! 🚀
