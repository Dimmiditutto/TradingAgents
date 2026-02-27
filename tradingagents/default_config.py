import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # Strategy type: "swing" (2-10 days) or "investing" (3+ months)
    "strategy_type": "swing",  # Options: "swing", "investing"
    
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, mcp_alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, mcp_alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, mcp_alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, mcp_alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "mcp_alpha_vantage",  # Override category default
        # MCP (Model Context Protocol) provides:
        #   - Standardized tool interface for LLMs
        #   - Automatic rate limiting and caching
        #   - Better error handling
        #   - Direct access to Alpha Vantage tools
    },
}


# ==================== SWING TRADING CONFIG ====================
SWING_CONFIG = DEFAULT_CONFIG.copy()
SWING_CONFIG.update({
    "strategy_type": "swing",
    "max_debate_rounds": 3,           # Più analisi per swing trading
    "max_risk_discuss_rounds": 2,     # Analisi rischio più approfondita
    "deep_think_llm": "gpt-5-mini",   # Velocità per decisioni rapide
    "quick_think_llm": "gpt-5-mini",  # Coerenza nella velocità
})


# ==================== INVESTING CONFIG ====================
INVESTING_CONFIG = DEFAULT_CONFIG.copy()
INVESTING_CONFIG.update({
    "strategy_type": "investing",
    "max_debate_rounds": 5,            # Analisi approfondita per long-term
    "max_risk_discuss_rounds": 3,      # Risk assessment strategico
    "deep_think_llm": "gpt-5.2",       # Modello potente per ragionamento complesso
    "quick_think_llm": "gpt-5.2",      # Qualità anche per analisi rapide
})

