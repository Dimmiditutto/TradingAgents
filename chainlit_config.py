"""
Configuration module for Chainlit parameter selection
Gestisce la raccolta interattiva dei parametri per l'analisi trading
"""

import chainlit as cl
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from enum import Enum

# Define AnalystType locally to avoid dependency on cli module
class AnalystType(str, Enum):
    MARKET = "market"
    SOCIAL = "social"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"

# Opzioni disponibili
ANALYST_OPTIONS = [
    ("Market Analyst", "market"),
    ("Social Media Analyst", "social"),
    ("News Analyst", "news"),
    ("Fundamentals Analyst", "fundamentals"),
]

RESEARCH_DEPTH_OPTIONS = [
    ("🚀 Shallow - Quick research, few debate rounds", 1),
    ("⚙️ Medium - Moderate debate and strategy discussion", 3),
    ("🔬 Deep - Comprehensive research with in-depth analysis", 5),
]

LLM_PROVIDER_OPTIONS = [
    ("🤖 OpenAI", "openai"),
    ("🧠 Anthropic (Claude)", "anthropic"),
    ("✨ Google Gemini", "google"),
    ("🌐 OpenRouter", "openrouter"),
    ("📦 Ollama (Local)", "ollama"),
]

SHALLOW_AGENT_OPTIONS = {
    "openai": [
        ("GPT-4o-mini - Fast and efficient", "gpt-4o-mini"),
        ("GPT-4.1-nano - Ultra-lightweight", "gpt-4.1-nano"),
        ("GPT-4.1-mini - Compact with good performance", "gpt-4.1-mini"),
        ("GPT-4o - Standard solid capabilities", "gpt-4o"),
    ],
    "anthropic": [
        ("Claude Haiku 3.5 - Fast inference", "claude-3-5-haiku-latest"),
        ("Claude Sonnet 3.5 - Highly capable", "claude-3-5-sonnet-latest"),
        ("Claude Sonnet 3.7 - Exceptional reasoning", "claude-3-7-sonnet-latest"),
        ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
    ],
    "google": [
        ("Gemini 2.0 Flash-Lite - Cost efficient", "gemini-2.0-flash-lite"),
        ("Gemini 2.0 Flash - Next generation", "gemini-2.0-flash"),
        ("Gemini 2.5 Flash - Adaptive thinking", "gemini-2.5-flash-preview-05-20"),
    ],
    "openrouter": [
        ("Meta: Llama 4 Scout", "meta-llama/llama-4-scout:free"),
        ("Meta: Llama 3.3 8B Instruct", "meta-llama/llama-3.3-8b-instruct:free"),
        ("Google: Gemini 2.0 Flash", "google/gemini-2.0-flash-exp:free"),
    ],
    "ollama": [
        ("Llama 3.1 local", "llama3.1"),
        ("Llama 3.2 local", "llama3.2"),
    ]
}

DEEP_AGENT_OPTIONS = {
    "openai": [
        ("GPT-4.1-nano - Ultra-lightweight", "gpt-4.1-nano"),
        ("GPT-4.1-mini - Compact model", "gpt-4.1-mini"),
        ("GPT-4o - Standard model", "gpt-4o"),
        ("o4-mini - Specialized reasoning (compact)", "o4-mini"),
        ("o3-mini - Advanced reasoning (lightweight)", "o3-mini"),
        ("o3 - Full advanced reasoning", "o3"),
        ("o1 - Premier reasoning model", "o1"),
    ],
    "anthropic": [
        ("Claude Haiku 3.5 - Fast inference", "claude-3-5-haiku-latest"),
        ("Claude Sonnet 3.5 - Highly capable", "claude-3-5-sonnet-latest"),
        ("Claude Sonnet 3.7 - Exceptional reasoning", "claude-3-7-sonnet-latest"),
        ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
        ("Claude Opus 4 - Most powerful", "claude-opus-4-0"),
    ],
    "google": [
        ("Gemini 2.0 Flash-Lite - Cost efficient", "gemini-2.0-flash-lite"),
        ("Gemini 2.0 Flash - Next generation", "gemini-2.0-flash"),
        ("Gemini 2.5 Flash - Adaptive thinking", "gemini-2.5-flash-preview-05-20"),
        ("Gemini 2.5 Pro", "gemini-2.5-pro-preview-06-05"),
    ],
    "openrouter": [
        ("DeepSeek V3 - 685B-parameter model", "deepseek/deepseek-chat-v3-0324:free"),
        ("DeepSeek Chat", "deepseek/deepseek-chat-v3-0324:free"),
    ],
    "ollama": [
        ("Llama 3.1 local", "llama3.1"),
        ("Qwen 3 local", "qwen3"),
    ]
}

BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/",
    "google": "https://generativelanguage.googleapis.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
}


async def ask_ticker() -> str:
    """Chiedi il ticker symbol"""
    response = await cl.AskUserMessage(
        content="""
📊 **Step 1: Ticker Symbol**

Quale titolo vuoi analizzare?

*Esempi: NVDA, AAPL, SPY, TSLA, BTC-USD*
        """,
        timeout=300
    ).send()
    
    if not response:
        return "SPY"
    # Handle both dict and object response types
    content = response.get("content") if isinstance(response, dict) else getattr(response, "content", None)
    return content.strip().upper() if content else "SPY"


async def ask_analysis_date() -> str:
    """Chiedi la data dell'analisi"""
    default_date = datetime.now().strftime("%Y-%m-%d")
    
    response = await cl.AskUserMessage(
        content=f"""
📅 **Step 2: Analysis Date**

Inserisci la data per l'analisi (formato: YYYY-MM-DD)

*Default: {default_date}*
        """,
        timeout=300
    ).send()
    
    if not response:
        return default_date
    # Handle both dict and object response types
    content = response.get("content") if isinstance(response, dict) else getattr(response, "content", None)
    if not content or not content.strip():
        return default_date
    
    return content.strip()


async def ask_analysts() -> List[str]:
    """Chiedi gli analisti da selezionare"""
    actions = [
        cl.Action(name=f"analyst_{value}", payload=value, label=label)
        for label, value in ANALYST_OPTIONS
    ]
    
    await cl.Message(
        content="""
👥 **Step 3: Select Analysts Team**

Seleziona i team di analisti che vuoi utilizzare:
        """
    ).send()
    
    selected = []
    
    for label, value in ANALYST_OPTIONS:
        response = await cl.AskActionMessage(
            content=f"**{label}** - Include in analysis?",
            actions=[
                cl.Action(name="yes", payload="yes", label="✅ Yes"),
                cl.Action(name="no", payload="no", label="❌ No"),
            ],
            timeout=60
        ).send()
        
        if response:
            # Handle both dict and object response types
            resp_value = response.get("payload") if isinstance(response, dict) else getattr(response, "payload", None)
            if resp_value == "yes":
                selected.append(value)
    
    if not selected:
        selected = ["market"]  # Default
        await cl.Message(
            content="⚠️ No analyst selected, using Market Analyst as default"
        ).send()
    
    await cl.Message(
        content=f"✅ Selected analysts: {', '.join(selected)}"
    ).send()
    
    return selected


async def ask_research_depth() -> int:
    """Chiedi la profondità della ricerca"""
    response = await cl.AskActionMessage(
        content="""
🔍 **Step 4: Research Depth**

Quale livello di profondità vuoi per la ricerca?
        """,
        actions=[
            cl.Action(name="shallow", payload=1, label="🚀 Shallow (1 round)"),
            cl.Action(name="medium", payload=3, label="⚙️ Medium (3 rounds)"),
            cl.Action(name="deep", payload=5, label="🔬 Deep (5 rounds)"),
        ],
        timeout=300
    ).send()
    
    if not response:
        return 3
    # Handle both dict and object response types
    value = response.get("payload") if isinstance(response, dict) else getattr(response, "payload", None)
    return int(value) if value else 3


async def ask_llm_provider() -> Tuple[str, str]:
    """Chiedi il provider LLM"""
    response = await cl.AskActionMessage(
        content="""
🤖 **Step 5: LLM Provider**

Quale provider LLM vuoi utilizzare?
        """,
        actions=[
            cl.Action(name=f"provider_{value}", payload=value, label=label)
            for label, value in LLM_PROVIDER_OPTIONS
        ],
        timeout=300
    ).send()
    
    if not response:
        provider = "openai"
    else:
        # Handle both dict and object response types
        provider = response.get("payload") if isinstance(response, dict) else getattr(response, "payload", "openai")
    backend_url = BASE_URLS.get(provider, "https://api.openai.com/v1")
    
    await cl.Message(
        content=f"✅ Selected provider: **{provider}**"
    ).send()
    
    return provider, backend_url


async def ask_shallow_thinking_agent(provider: str) -> str:
    """Chiedi il modello per il quick thinking"""
    options = SHALLOW_AGENT_OPTIONS.get(provider.lower(), SHALLOW_AGENT_OPTIONS["openai"])
    
    actions = [
        cl.Action(name=f"shallow_{value}", payload=value, label=label)
        for label, value in options
    ]
    
    response = await cl.AskActionMessage(
        content=f"""
⚡ **Step 6a: Quick-Thinking LLM Model**

Seleziona il modello per il quick thinking (analisi veloce):
        """,
        actions=actions[:4],  # Mostra i primi 4 per evitare troppe opzioni
        timeout=300
    ).send()
    
    if not response:
        model = options[0][1]
    else:
        # Handle both dict and object response types
        model = response.get("payload") if isinstance(response, dict) else getattr(response, "payload", options[0][1])
    
    await cl.Message(
        content=f"✅ Quick-Thinking Model: **{model}**"
    ).send()
    
    return model


async def ask_deep_thinking_agent(provider: str) -> str:
    """Chiedi il modello per il deep thinking"""
    options = DEEP_AGENT_OPTIONS.get(provider.lower(), DEEP_AGENT_OPTIONS["openai"])
    
    actions = [
        cl.Action(name=f"deep_{value}", payload=value, label=label)
        for label, value in options
    ]
    
    response = await cl.AskActionMessage(
        content=f"""
🧠 **Step 6b: Deep-Thinking LLM Model**

Seleziona il modello per il deep thinking (analisi approfondita):
        """,
        actions=actions[:4],  # Mostra i primi 4 per evitare troppe opzioni
        timeout=300
    ).send()
    
    if not response:
        model = options[0][1]
    else:
        # Handle both dict and object response types
        model = response.get("payload") if isinstance(response, dict) else getattr(response, "payload", options[0][1])
    
    await cl.Message(
        content=f"✅ Deep-Thinking Model: **{model}**"
    ).send()
    
    return model


async def collect_parameters() -> Dict:
    """
    Raccogli tutti i parametri in modo interattivo
    """
    await cl.Message(
        content="""
🚀 **TradingAgents - Parameter Configuration**

Stiamo per configurare la tua analisi trading. Rispondi alle domande seguenti:
        """
    ).send()
    
    # Raccogli i parametri uno per uno
    ticker = await ask_ticker()
    
    analysis_date = await ask_analysis_date()
    
    analysts = await ask_analysts()
    
    research_depth = await ask_research_depth()
    
    llm_provider, backend_url = await ask_llm_provider()
    
    shallow_thinker = await ask_shallow_thinking_agent(llm_provider)
    
    deep_thinker = await ask_deep_thinking_agent(llm_provider)
    
    # Mostra il riepilogo
    await cl.Message(
        content=f"""
✅ **Configuration Summary**

📊 **Analysis Parameters:**
- **Ticker:** `{ticker}`
- **Date:** `{analysis_date}`
- **Analysts:** {', '.join(analysts)}
- **Research Depth:** Level {research_depth}
- **LLM Provider:** {llm_provider}
- **Quick-Thinking Model:** {shallow_thinker}
- **Deep-Thinking Model:** {deep_thinker}

Ready to start analysis! 🎯
        """
    ).send()
    
    return {
        "ticker": ticker,
        "analysis_date": analysis_date,
        "analysts": [AnalystType(a) for a in analysts],
        "research_depth": research_depth,
        "llm_provider": llm_provider,
        "backend_url": backend_url,
        "shallow_thinker": shallow_thinker,
        "deep_thinker": deep_thinker,
    }
