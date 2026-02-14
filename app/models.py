from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


# ── Request Models ──────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    symbol: str


class PortfolioAddRequest(BaseModel):
    symbol: str
    shares: float = Field(gt=0)
    avg_cost: float = Field(gt=0)


class PortfolioRemoveRequest(BaseModel):
    symbol: str


class AlertCreateRequest(BaseModel):
    symbol: str
    condition: str = Field(pattern=r"^(above|below)$")
    price: float = Field(gt=0)


class WatchlistModifyRequest(BaseModel):
    symbol: str


# ── Response Models ─────────────────────────────────────────────


class SymbolData(BaseModel):
    symbol: str
    price: float | None = None
    change_pct: float | None = None
    technicals: dict[str, Any] = {}
    signal_summary: str = ""
    news: list[dict[str, Any]] = []


class BriefingResponse(BaseModel):
    ai_summary: str
    watchlist_data: list[SymbolData]
    timestamp: datetime


class AnalysisResponse(BaseModel):
    symbol: str
    price: float | None = None
    change_pct: float | None = None
    technicals: dict[str, Any] = {}
    signal_summary: str = ""
    news: list[dict[str, Any]] = []
    ai_analysis: str = ""
    ai_recommendation: str = ""


class PortfolioResponse(BaseModel):
    holdings: list[dict[str, Any]]
    total_value: float
    daily_pnl: float
    ai_summary: str


class AlertCheckResponse(BaseModel):
    triggered: list[dict[str, Any]]
    message: str


class HealthResponse(BaseModel):
    status: str
    llm_connected: bool
    provider: str
    model: str
