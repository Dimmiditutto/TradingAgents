# TradingAgents - Chainlit Configuration Guide

## Nuova Funzionalità: Setup Guidato Interattivo 🎯

Ora puoi configurare completamente TradingAgents direttamente da Chainlit con il comando **`CONFIGURA`**!

## Come Funziona

### Opzione 1: Setup Guidato (Consigliato) ⭐

Digita `CONFIGURA` o `SETUP` e rispondi alle seguenti domande:

#### 1️⃣ Ticker Symbol
- Quale titolo vuoi analizzare?
- Esempi: NVDA, AAPL, SPY, BTC-USD
- Default: SPY

#### 2️⃣ Analysis Date
- Data per l'analisi (formato YYYY-MM-DD)
- Default: data corrente

#### 3️⃣ Analysts Team
Per ogni analista puoi scegliere:
- **Market Analyst** - Analisi tecnica e dei prezzi
- **Social Media Analyst** - Sentiment dai social media
- **News Analyst** - Analisi delle notizie
- **Fundamentals Analyst** - Analisi fondamentali

Seleziona uno o più analisti per personalizzare l'analisi.

#### 4️⃣ Research Depth
Scegli il livello di profondità:
- **🚀 Shallow (1 round)** - Analisi veloce
- **⚙️ Medium (3 rounds)** - Equilibrio tra velocità e qualità
- **🔬 Deep (5 rounds)** - Ricerca approfondita

#### 5️⃣ LLM Provider
Seleziona il provider per i modelli di linguaggio:
- **🤖 OpenAI** - GPT-4 e ultimi modelli
- **🧠 Anthropic (Claude)** - Modelli Claude
- **✨ Google Gemini** - Gemini
- **🌐 OpenRouter** - Accesso a più provider
- **📦 Ollama (Local)** - Esecuzione locale

#### 6️⃣ Thinking Models
Scegli i modelli per:
- **Quick-Thinking Model** (analisi veloce)
- **Deep-Thinking Model** (analisi approfondita)

Le opzioni disponibili dipendono dal provider scelto.

### Opzione 2: Comando Rapido

Se non vuoi fare il setup guidato, puoi usare direttamente:

```
ANALIZZA <TICKER> [DATA]
```

Esempi:
- `ANALIZZA NVDA` - Analizza NVDA con parametri di default
- `ANALIZZA AAPL 2024-05-10` - Analizza AAPL per una data specifica

**Nota:** Senza `CONFIGURA`, verranno usati i parametri di default.

## Comandi Disponibili

| Comando | Descrizione |
|---------|-------------|
| `CONFIGURA` | Avvia il setup guidato interattivo |
| `ANALIZZA <TICKER>` | Analizza un titolo |
| `ANALIZZA <TICKER> <DATA>` | Analizza un titolo per una data specifica |
| `LISTA` | Mostra asset supportati |
| `AIUTO` | Mostra la guida completa |

## Flusso Consigliato

1. **Primo accesso:**
   ```
   CONFIGURA
   ```
   Segui il wizard per configurare i tuoi parametri preferiti.

2. **Dopo il setup:**
   ```
   ANALIZZA NVDA
   ```
   L'analisi userà i parametri che hai configurato.

3. **Con data specifica:**
   ```
   ANALIZZA AAPL 2024-05-10
   ```
   Usa la configurazione ma analizza una data specifica.

## Output dell'Analisi

Per ogni analisi riceverai:

✅ **Decisione Trading**
- 💚 ACQUISTO (rialzista)
- ❌ VENDITA (ribassista)  
- ⏳ ATTESA (neutro)

✅ **Consensus Agenti**
- Sentiment complessivo
- Breakdown per team

✅ **File Scaricabili**
- **Dashboard HTML** - Visualizzazione interattiva con grafici
- **Report PDF** - Analisi formale completa
- **Dati Excel** - Per ulteriori analisi

## Parametri Salvati

Una volta che hai eseguito `CONFIGURA`, i tuoi parametri rimangono salvati per la sessione corrente.

Per cambiare i parametri, digita di nuovo:
```
CONFIGURA
```

## Esempi Pratici

### Esempio 1: Setup Completo + Analisi

```
Utente: CONFIGURA
App: [Mostra domande...]
Utente: NVDA
Utente: 2024-05-10
Utente: ✅ Market Analyst, ✅ News Analyst
Utente: Medium (3 rounds)
Utente: OpenAI
Utente: GPT-4o-mini
Utente: GPT-4o

App: ✅ Configuration saved!

Utente: ANALIZZA NVDA
App: [Esegue analisi di NVDA per 2024-05-10 con i tuoi parametri]
```

### Esempio 2: Analisi Rapida Senza Setup

```
Utente: ANALIZZA SPY
App: ⚠️ No custom configuration found
    Stai utilizzando i parametri di default...
    [Esegue analisi con parametri default]
```

## Provider LLM Supportati

### OpenAI
- `gpt-4o-mini` - Velocissimo, efficiente
- `gpt-4.1-nano` - Ultra-leggero
- `gpt-4.1-mini` - Compatto, buone prestazioni
- `gpt-4o` - Standard solido
- `o3-mini`, `o3`, `o1` - Modelli di ragionamento specializzati

### Anthropic (Claude)
- `claude-3-5-haiku-latest` - Inferenza veloce
- `claude-3-5-sonnet-latest` - Altamente capace
- `claude-3-7-sonnet-latest` - Ragionamento eccezionale
- `claude-sonnet-4-0` - Alta performance
- `claude-opus-4-0` - Più potente

### Google Gemini
- `gemini-2.0-flash-lite` - Efficiente
- `gemini-2.0-flash` - Nuova generazione
- `gemini-2.5-flash` - Pensiero adattivo
- `gemini-2.5-pro` - Prestazioni elevate

### OpenRouter
- Accesso a DeepSeek V3 e altri modelli
- API unificata per più provider

### Ollama (Local)
- `llama3.1` - Esecuzione locale
- `llama3.2` - Versione aggiornata
- `qwen3` - Modello Qwen

## Risoluzione Problemi

### "No custom configuration found"
- È normale se è il primo accesso
- Digita `CONFIGURA` per impostare i parametri
- Altrimenti usa parametri di default

### Errore durante l'analisi
- Verifica di aver inserito un ticker valido
- Controlla la connessione internet
- Assicurati che le API keys siano configurate

### L'analisi è lenta
- Prova con "Shallow" al posto di "Deep"
- Usa modelli più veloci (GPT-4o-mini, Claude Haiku)

## Note Importanti

⚠️ **Disclaimer:** Questo è uno strumento di analisi. Consulta sempre un esperto prima di fare operazioni di trading.

🔑 **API Keys:** Assicurati di aver configurato le credenziali per i provider che usi:
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Google: `GOOGLE_API_KEY`
- OpenRouter: `OPENROUTER_API_KEY`

💡 **Migliori Risultati:** 
- Usa almeno 6 mesi di dati storici
- Combina più analisti per consensus migliore
- Usa "Deep" research per decisioni importanti
