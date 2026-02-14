import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yfinance as yf
from crewai import Crew, Task, Process
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
from agents import strategy_reporter, get_provider_info, OLLAMA_URL, LLM_PROVIDER
from tools import FetchStockDataTool, TechnicalAnalysisTool, FetchNewsTool
from models import (
    AnalysisResponse,
    AlertCheckResponse,
    AlertCreateRequest,
    BriefingResponse,
    HealthResponse,
    PortfolioAddRequest,
    PortfolioRemoveRequest,
    PortfolioResponse,
    SymbolData,
    WatchlistModifyRequest,
)

load_dotenv()

# ── Shared tool instances for direct data fetching ──────────────

_stock_tool = FetchStockDataTool()
_ta_tool = TechnicalAnalysisTool()
_news_tool = FetchNewsTool()


def _fetch_symbol_data(symbol: str, period: str = "1mo") -> SymbolData:
    """Fetch real data for a symbol directly from tools (no LLM)."""
    # Price data
    price = None
    change_pct = None
    try:
        stock_raw = json.loads(_stock_tool._run(symbol=symbol, period=period))
        if "error" not in stock_raw:
            price = stock_raw.get("current_price")
            change_pct = stock_raw.get("change_pct")
    except Exception:
        pass

    # Technicals
    technicals = {}
    signal_summary = ""
    try:
        ta_raw = json.loads(_ta_tool._run(symbol=symbol))
        if "error" not in ta_raw:
            technicals = ta_raw.get("indicators", {})
            signal_summary = ta_raw.get("signal_summary", "")
    except Exception:
        pass

    # News
    news = []
    try:
        news_raw = json.loads(_news_tool._run(symbol=symbol))
        if "error" not in news_raw:
            news = news_raw.get("articles", [])
    except Exception:
        pass

    return SymbolData(
        symbol=symbol.upper(),
        price=price,
        change_pct=change_pct,
        technicals=technicals,
        signal_summary=signal_summary,
        news=news,
    )


def _symbol_data_to_text(data: SymbolData) -> str:
    """Convert SymbolData to plain text for LLM context."""
    lines = [f"## {data.symbol}"]
    if data.price is not None:
        lines.append(f"- Current Price: ${data.price}")
    if data.change_pct is not None:
        lines.append(f"- Change: {data.change_pct:+.2f}%")
    if data.signal_summary:
        lines.append(f"- Signals: {data.signal_summary}")
    if data.technicals:
        lines.append("- Technicals:")
        for k, v in data.technicals.items():
            if v is not None:
                lines.append(f"  - {k}: {v}")
    if data.news:
        lines.append("- Recent News:")
        for article in data.news[:5]:
            title = article.get("title", "No title")
            publisher = article.get("publisher", "")
            lines.append(f"  - {title} ({publisher})")
    else:
        lines.append("- Recent News: No recent news found.")
    return "\n".join(lines)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="StockBot API",
    description="AI-powered stock market assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static UI ─────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    return {"message": "StockBot API — visit /docs for API documentation"}


# ── Health ──────────────────────────────────────────────────────


@app.get("/health")
async def health():
    info = get_provider_info()
    provider = info["provider"]
    llm_ok = False

    if provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{OLLAMA_URL}/api/tags")
                llm_ok = resp.status_code == 200
        except Exception:
            pass
    else:
        # Cloud providers — check if API key is set
        key_env = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_var = key_env.get(provider, "")
        llm_ok = bool(os.environ.get(env_var))

    return {
        "status": "ok" if llm_ok else "degraded",
        "llm_connected": llm_ok,
        "provider": provider,
        "model": info["model"],
    }


# ── Briefing ────────────────────────────────────────────────────


@app.post("/briefing", response_model=BriefingResponse)
async def briefing():
    symbols = database.get_watchlist()
    if not symbols:
        raise HTTPException(status_code=400, detail="Watchlist is empty")

    # 1. Fetch real data directly (no LLM)
    all_data: list[SymbolData] = []
    for sym in symbols:
        all_data.append(_fetch_symbol_data(sym))

    # 2. Build context text for the LLM
    context = "Here is the REAL market data. Use ONLY these numbers:\n\n"
    for d in all_data:
        context += _symbol_data_to_text(d) + "\n\n"

    # 3. Run only the Reporter agent to interpret the data
    reporter = strategy_reporter()

    task_report = Task(
        description=(
            f"You are given real market data below. Do NOT invent any prices, "
            f"percentages, or news headlines. Use ONLY the data provided.\n\n"
            f"{context}\n"
            f"Write a morning briefing that includes for each symbol:\n"
            f"1) Current price and daily change\n"
            f"2) Key technical signals interpretation\n"
            f"3) News highlights (only from the data above, or say 'No recent news')\n"
            f"4) Brief outlook (bullish/bearish/neutral with reasoning)\n"
            f"End with a short market overview."
        ),
        expected_output="A morning briefing using only the provided data.",
        agent=reporter,
    )

    crew = Crew(
        agents=[reporter],
        tasks=[task_report],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    return BriefingResponse(
        ai_summary=str(result),
        watchlist_data=all_data,
        timestamp=datetime.now(timezone.utc),
    )


# ── Quick Data (no AI, instant for UI) ──────────────────────────


@app.get("/quote/{symbol}")
async def quote(symbol: str):
    """Fast data-only endpoint for UI — no LLM, returns instantly."""
    data = _fetch_symbol_data(symbol.upper())
    return data


# ── Single Stock Analysis (with AI) ─────────────────────────────


@app.get("/analyze/{symbol}", response_model=AnalysisResponse)
async def analyze(symbol: str):
    symbol = symbol.upper()

    # 1. Fetch real data directly
    data = _fetch_symbol_data(symbol, period="3mo")
    context = _symbol_data_to_text(data)

    # 2. Run only the Reporter to interpret
    reporter = strategy_reporter()

    task_report = Task(
        description=(
            f"You are given real market data below. Do NOT invent any prices, "
            f"percentages, or news headlines. Use ONLY the data provided.\n\n"
            f"{context}\n\n"
            f"Produce a full analysis for {symbol}:\n"
            f"1) Price summary with key levels\n"
            f"2) Technical indicator interpretation\n"
            f"3) News impact assessment (only from data above)\n"
            f"4) Clear buy/hold/sell recommendation with reasoning\n\n"
            f"End your response with a single line starting with 'RECOMMENDATION:' "
            f"followed by BUY, HOLD, or SELL and a one-sentence reason."
        ),
        expected_output=f"Analysis and recommendation for {symbol} using only provided data.",
        agent=reporter,
    )

    crew = Crew(
        agents=[reporter],
        tasks=[task_report],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    report_text = str(result)

    # Extract recommendation line
    recommendation = ""
    for line in report_text.splitlines():
        if line.strip().upper().startswith("RECOMMENDATION:"):
            recommendation = line.strip()
            break
    if not recommendation:
        recommendation = report_text.split("\n")[-1].strip()

    return AnalysisResponse(
        symbol=symbol,
        price=data.price,
        change_pct=data.change_pct,
        technicals=data.technicals,
        signal_summary=data.signal_summary,
        news=data.news,
        ai_analysis=report_text,
        ai_recommendation=recommendation,
    )


# ── Portfolio ───────────────────────────────────────────────────


@app.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    holdings = database.get_portfolio()

    if not holdings:
        return PortfolioResponse(
            holdings=[],
            total_value=0.0,
            daily_pnl=0.0,
            ai_summary="Portfolio is empty. Add holdings with POST /portfolio.",
        )

    # 1. Compute real values directly
    total_value = 0.0
    daily_pnl = 0.0
    enriched = []
    context_lines = ["Portfolio positions:"]

    for h in holdings:
        try:
            info = yf.Ticker(h["symbol"]).info
            price = info.get("regularMarketPrice") or info.get("previousClose", 0)
            prev = info.get("previousClose", price)
        except Exception:
            price = 0
            prev = 0
        val = price * h["shares"]
        pnl = (price - prev) * h["shares"]
        unrealized = (price - h["avg_cost"]) * h["shares"]
        total_value += val
        daily_pnl += pnl
        enriched.append({
            "symbol": h["symbol"],
            "shares": h["shares"],
            "avg_cost": h["avg_cost"],
            "current_price": round(price, 2),
            "value": round(val, 2),
            "daily_pnl": round(pnl, 2),
            "unrealized_pnl": round(unrealized, 2),
        })
        context_lines.append(
            f"- {h['symbol']}: {h['shares']} shares @ avg ${h['avg_cost']}, "
            f"now ${round(price, 2)}, value ${round(val, 2)}, "
            f"daily P&L ${round(pnl, 2)}, unrealized ${round(unrealized, 2)}"
        )

    context_lines.append(f"\nTotal Value: ${round(total_value, 2)}")
    context_lines.append(f"Daily P&L: ${round(daily_pnl, 2)}")
    context = "\n".join(context_lines)

    # 2. Run Reporter for summary
    reporter = strategy_reporter()

    task_report = Task(
        description=(
            f"You are given real portfolio data below. Use ONLY these numbers.\n\n"
            f"{context}\n\n"
            f"Write a brief portfolio summary: total value, daily P&L, "
            f"top movers, and any positions needing attention."
        ),
        expected_output="Brief portfolio summary using only provided data.",
        agent=reporter,
    )

    crew = Crew(
        agents=[reporter],
        tasks=[task_report],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    return PortfolioResponse(
        holdings=enriched,
        total_value=round(total_value, 2),
        daily_pnl=round(daily_pnl, 2),
        ai_summary=str(result),
    )


@app.post("/portfolio")
async def modify_portfolio(req: PortfolioAddRequest):
    holding = database.add_holding(req.symbol, req.shares, req.avg_cost)
    return {"status": "added", "holding": holding}


@app.delete("/portfolio/{symbol}")
async def delete_portfolio(symbol: str):
    removed = database.remove_holding(symbol)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in portfolio")
    return {"status": "removed", "symbol": symbol.upper()}


# ── Watchlist ───────────────────────────────────────────────────


@app.get("/watchlist")
async def get_watchlist():
    return {"symbols": database.get_watchlist()}


@app.post("/watchlist")
async def add_watchlist(req: WatchlistModifyRequest):
    database.add_to_watchlist(req.symbol)
    return {"status": "added", "symbol": req.symbol.upper()}


@app.delete("/watchlist/{symbol}")
async def remove_watchlist(symbol: str):
    removed = database.remove_from_watchlist(symbol)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    return {"status": "removed", "symbol": symbol.upper()}


# ── Alerts ──────────────────────────────────────────────────────


@app.get("/alerts")
async def list_alerts():
    return {"alerts": database.get_alerts()}


@app.post("/alerts")
async def create_alert(req: AlertCreateRequest):
    alert = database.add_alert(req.symbol, req.condition, req.price)
    return {"status": "created", "alert": alert}


@app.post("/check-alerts", response_model=AlertCheckResponse)
async def check_alerts():
    alerts = database.get_alerts(active_only=True)

    if not alerts:
        return AlertCheckResponse(triggered=[], message="No active alerts.")

    # Group alerts by symbol to minimize API calls
    symbols = list({a["symbol"] for a in alerts})
    prices = {}
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            prices[sym] = info.get("regularMarketPrice") or info.get("previousClose", 0)
        except Exception:
            prices[sym] = 0

    triggered = []
    for alert in alerts:
        sym = alert["symbol"]
        price = prices.get(sym, 0)
        if price == 0:
            continue

        fired = False
        if alert["condition"] == "above" and price >= alert["price"]:
            fired = True
        elif alert["condition"] == "below" and price <= alert["price"]:
            fired = True

        if fired:
            database.deactivate_alert(alert["id"])
            triggered.append({
                "id": alert["id"],
                "symbol": sym,
                "condition": alert["condition"],
                "target_price": alert["price"],
                "current_price": round(price, 2),
            })

    if triggered:
        message = f"{len(triggered)} alert(s) triggered."
    else:
        message = "No alerts triggered. All conditions still pending."

    return AlertCheckResponse(triggered=triggered, message=message)
