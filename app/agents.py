import logging
import os

# Suppress noisy LiteLLM proxy import warnings (we don't use the proxy)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
os.environ.setdefault("LITELLM_LOG", "WARNING")

from crewai import Agent, LLM

from tools import (
    FetchStockDataTool,
    TechnicalAnalysisTool,
    FetchNewsTool,
    PortfolioDataTool,
)

# ── LLM Configuration ──────────────────────────────────────────

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")

# Provider → LiteLLM model prefix mapping
_PROVIDER_PREFIX = {
    "ollama": "ollama/",
    "gemini": "gemini/",
    "openai": "openai/",
    "anthropic": "anthropic/",
}

# Default models per provider (used if LLM_MODEL not set explicitly)
_PROVIDER_DEFAULTS = {
    "ollama": "qwen2.5:7b",
    "gemini": "gemini-3-pro-preview",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
}


def get_llm() -> LLM:
    provider = LLM_PROVIDER.lower()
    prefix = _PROVIDER_PREFIX.get(provider, "")
    model = LLM_MODEL or _PROVIDER_DEFAULTS.get(provider, "qwen2.5:7b")
    model_string = f"{prefix}{model}"

    kwargs = {"model": model_string, "temperature": 0.3}

    # Ollama needs base_url, cloud providers read API keys from env automatically
    if provider == "ollama":
        kwargs["base_url"] = OLLAMA_URL

    return LLM(**kwargs)


def get_provider_info() -> dict:
    """Return current LLM provider info for health endpoint."""
    provider = LLM_PROVIDER.lower()
    model = LLM_MODEL or _PROVIDER_DEFAULTS.get(provider, "unknown")
    return {"provider": provider, "model": model}


# ── Tool instances ──────────────────────────────────────────────

fetch_stock_data = FetchStockDataTool()
technical_analysis = TechnicalAnalysisTool()
fetch_news = FetchNewsTool()
portfolio_data = PortfolioDataTool()


# ── Agent definitions ───────────────────────────────────────────


def market_data_analyst() -> Agent:
    return Agent(
        role="Market Data Analyst",
        goal=(
            "Gather comprehensive price data, technical indicators, and portfolio "
            "positions for the requested stock symbols."
        ),
        backstory=(
            "You are an expert quantitative analyst who specializes in fetching "
            "and processing raw market data. You pull OHLCV data, compute technical "
            "indicators, and assess portfolio positions with precision."
        ),
        tools=[fetch_stock_data, technical_analysis, portfolio_data],
        llm=get_llm(),
        max_iter=3,
        verbose=True,
    )


def news_analyst() -> Agent:
    return Agent(
        role="News Analyst",
        goal=(
            "Find and summarize recent market news for the requested symbols. "
            "Assess overall sentiment as bullish, bearish, or neutral."
        ),
        backstory=(
            "You are a seasoned financial journalist who tracks breaking news, "
            "earnings reports, and market-moving events. You distill headlines "
            "into concise summaries with clear sentiment assessments."
        ),
        tools=[fetch_news],
        llm=get_llm(),
        max_iter=3,
        verbose=True,
    )


def strategy_reporter() -> Agent:
    return Agent(
        role="Strategy Reporter",
        goal=(
            "Synthesize market data and news into actionable insights. Produce "
            "clear, concise summaries with buy/hold/sell signals and reasoning."
        ),
        backstory=(
            "You are a senior investment strategist who combines technical analysis "
            "with fundamental news to form well-reasoned market views. You communicate "
            "complex analysis in plain English that any investor can understand."
        ),
        tools=[],
        llm=get_llm(),
        max_iter=2,
        verbose=True,
    )
