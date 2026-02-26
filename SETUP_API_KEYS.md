# 🔑 Setup API Keys per TradingAgents Chainlit

## Come Configurare le API keys

### ⚠️ IMPORTANTE
Devi impostare almeno una API key prima di poter usare TradingAgents!

---

## 1️⃣ OpenAI (Consigliato)

### Passo 1: Vai al sito OpenAI
```
https://platform.openai.com/api-keys
```

### Passo 2: Accedi o crea un account
- Usa il tuo account OpenAI
- Se non hai un account, creane uno

### Passo 3: Genera una nuova API key
1. Clicca su "Create new secret key"
2. Dai un nome alla key (es. "TradingAgents")
3. Copia la chiave (non puoi vederla di nuovo!)

### Passo 4: Configura il file `.env`
Apri `/workspaces/TradingAgents/web/.env` e aggiungi:

```
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### Passo 5: Salva il file
- Salva il file
- Riavvia Chainlit

---

## 2️⃣ Alternativa: Anthropic Claude

Se preferisci usare Claude di Anthropic:

### Ottieni la API key
```
https://console.anthropic.com/
```

### Configura `.env`
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Nel setup Chainlit
Durante il wizard `CONFIGURA`, seleziona "Anthropic" come provider

---

## 3️⃣ Alternativa: Google Gemini

### Ottieni la API key
```
https://aistudio.google.com/
```

### Configura `.env`
```
GOOGLE_API_KEY=AIzaSy...
```

### Nel setup Chainlit
Durante il wizard `CONFIGURA`, seleziona "Google" come provider

---

## ✅ Verifica che Funziona

Dopo aver aggiunto la API key:

1. Riavvia Chainlit
2. Vai a http://localhost:8000
3. Digita `CONFIGURA`
4. Procedi con il wizard

Se vedi messaggi di benvenuto, **funziona!** 🎉

---

## 🔒 Sicurezza

**IMPORTANTE:**
- ❌ NON mettere il file `.env` su GitHub
- ❌ NON condividere la tua API key con nessuno
- ✅ Il file `.env` è già in `.gitignore` (protetto)
- ✅ Mantieni segreta la tua API key!

---

## 💰 Costi

**OpenAI:**
- Paghi solo per quello che usi
- Primi $5 di credito gratuito
- Modelli disponibili: GPT-4, GPT-4o-mini, etc.

**Anthropic (Claude):**
- Pricing a consumo
- Accesso ai modelli Claude

**Google Gemini:**
- Free tier disponibile
- Accesso ai modelli Gemini

---

## ❌ Errore: "api_key must be set"

Se ricevi questo errore:

1. Verifica di aver creato il file `.env`
2. Verifica di aver aggiunto una API key
3. Verifica che il file sia in: `/workspaces/TradingAgents/web/.env`
4. Riavvia Chainlit

---

## 📝 Checklist di Setup

- [ ] Ho creato un account sul sito LLM (OpenAI/Anthropic/Google)
- [ ] Ho generato una API key
- [ ] Ho copiato la API key
- [ ] Ho aperto `/workspaces/TradingAgents/web/.env`
- [ ] Ho aggiunto `OPENAI_API_KEY=sk-...` (o altro provider)
- [ ] Ho salvato il file
- [ ] Ho riavviato Chainlit

Dopo questi step, sei pronto! 🚀

---

## 🆘 Supporto

Se hai problemi:

1. Verifica che il file `.env` esista in `/workspaces/TradingAgents/web/`
2. Verifica che non ci siano spazi in più nella API key
3. Verifica che la API key sia corretta (copiata bene)
4. Prova a rigenerare una nuova API key dal sito

Buona analisi! 🎯
