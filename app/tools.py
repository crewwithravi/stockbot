import json
from datetime import datetime, timezone
from typing import Type

import yfinance as yf
import pandas as pd
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

import database


# ── Tool Input Schemas ──────────────────────────────────────────


class StockSymbolInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. QQQ, AAPL)")


class StockDataInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. QQQ, AAPL)")
    period: str = Field(
        default="1mo",
        description="Data period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max",
    )


# ── Tool 1: FetchStockDataTool ──────────────────────────────────


class FetchStockDataTool(BaseTool):
    name: str = "fetch_stock_data"
    description: str = (
        "Fetch OHLCV price data and company info for a stock symbol. "
        "Returns current price, change %, 52-week high/low, volume, market cap, "
        "and recent candles."
    )
    args_schema: Type[BaseModel] = StockDataInput

    def _run(self, symbol: str, period: str = "1mo") -> str:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return json.dumps({"error": f"No data found for {symbol}"})

            info = ticker.info
            latest = hist.iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else latest["Close"]
            change_pct = ((latest["Close"] - prev_close) / prev_close) * 100

            candles = []
            for idx, row in hist.tail(10).iterrows():
                candles.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })

            result = {
                "symbol": symbol.upper(),
                "current_price": round(latest["Close"], 2),
                "change_pct": round(change_pct, 2),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "volume": int(latest["Volume"]),
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "recent_candles": candles,
            }
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})


# ── Tool 2: TechnicalAnalysisTool ───────────────────────────────


class TechnicalAnalysisTool(BaseTool):
    name: str = "technical_analysis"
    description: str = (
        "Compute technical indicators for a stock: RSI(14), MACD(12,26,9), "
        "SMA(20/50/200), Bollinger Bands, and ATR. Returns indicator values "
        "plus a plain-English signal summary."
    )
    args_schema: Type[BaseModel] = StockSymbolInput

    def _run(self, symbol: str) -> str:
        try:
            from ta.momentum import RSIIndicator
            from ta.trend import MACD, SMAIndicator
            from ta.volatility import BollingerBands, AverageTrueRange

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")

            if hist.empty:
                return json.dumps({"error": f"No data found for {symbol}"})

            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]

            # RSI
            rsi_ind = RSIIndicator(close, window=14)
            rsi_val = round(rsi_ind.rsi().iloc[-1], 2)

            # MACD
            macd_ind = MACD(close, window_slow=26, window_fast=12, window_sign=9)
            macd_val = round(macd_ind.macd().iloc[-1], 2)
            macd_signal = round(macd_ind.macd_signal().iloc[-1], 2)
            macd_hist = round(macd_ind.macd_diff().iloc[-1], 2)

            # SMAs
            sma20_val = round(SMAIndicator(close, window=20).sma_indicator().iloc[-1], 2)
            sma50_val = round(SMAIndicator(close, window=50).sma_indicator().iloc[-1], 2)
            sma200_s = SMAIndicator(close, window=200).sma_indicator()
            sma200_val = round(sma200_s.iloc[-1], 2) if not sma200_s.isna().iloc[-1] else None

            # Bollinger Bands
            bb = BollingerBands(close, window=20, window_dev=2)
            bb_upper = round(bb.bollinger_hband().iloc[-1], 2)
            bb_middle = round(bb.bollinger_mavg().iloc[-1], 2)
            bb_lower = round(bb.bollinger_lband().iloc[-1], 2)

            # ATR
            atr_ind = AverageTrueRange(high, low, close, window=14)
            atr_val = round(atr_ind.average_true_range().iloc[-1], 2)

            current_price = round(close.iloc[-1], 2)

            # Build signal summary
            signals = []
            if rsi_val > 70:
                signals.append(f"RSI({rsi_val}) indicates OVERBOUGHT")
            elif rsi_val < 30:
                signals.append(f"RSI({rsi_val}) indicates OVERSOLD")
            else:
                signals.append(f"RSI({rsi_val}) is neutral")

            if macd_val > macd_signal:
                signals.append("MACD is above signal line (bullish)")
            else:
                signals.append("MACD is below signal line (bearish)")

            if sma200_val is not None:
                if sma50_val > sma200_val:
                    signals.append("Golden cross: SMA50 above SMA200 (bullish)")
                else:
                    signals.append("Death cross: SMA50 below SMA200 (bearish)")

            if current_price > bb_upper:
                signals.append("Price above upper Bollinger Band (overbought)")
            elif current_price < bb_lower:
                signals.append("Price below lower Bollinger Band (oversold)")

            result = {
                "symbol": symbol.upper(),
                "current_price": current_price,
                "indicators": {
                    "rsi_14": rsi_val,
                    "macd": macd_val,
                    "macd_signal": macd_signal,
                    "macd_histogram": macd_hist,
                    "sma_20": sma20_val,
                    "sma_50": sma50_val,
                    "sma_200": sma200_val,
                    "bollinger_upper": bb_upper,
                    "bollinger_middle": bb_middle,
                    "bollinger_lower": bb_lower,
                    "atr_14": atr_val,
                },
                "signal_summary": "; ".join(signals) if signals else "Insufficient data for signals",
            }
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})


# ── Tool 3: FetchNewsTool ───────────────────────────────────────


class FetchNewsTool(BaseTool):
    name: str = "fetch_news"
    description: str = (
        "Fetch recent news headlines for a stock symbol using yfinance. "
        "Returns up to 10 recent articles with title, publisher, link, and time."
    )
    args_schema: Type[BaseModel] = StockSymbolInput

    def _run(self, symbol: str) -> str:
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news

            if not news:
                return json.dumps({"symbol": symbol.upper(), "articles": [], "message": "No recent news found"})

            articles = []
            for item in news[:10]:
                # yfinance 1.1.0+ nests data under "content"
                content = item.get("content", item)
                title = content.get("title", "")
                if not title:
                    continue

                provider = content.get("provider", {})
                publisher = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)

                link_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
                link = link_obj.get("url", "") if isinstance(link_obj, dict) else str(link_obj)

                pub_date = content.get("pubDate") or content.get("displayTime")

                articles.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "publish_time": pub_date,
                })

            if not articles:
                return json.dumps({"symbol": symbol.upper(), "articles": [], "message": "No recent news found"})

            return json.dumps({"symbol": symbol.upper(), "articles": articles})
        except Exception as e:
            return json.dumps({"error": str(e)})


# ── Tool 4: PortfolioDataTool ───────────────────────────────────


class _EmptyInput(BaseModel):
    pass


class PortfolioDataTool(BaseTool):
    name: str = "portfolio_data"
    description: str = (
        "Fetch current prices and compute P&L for all holdings in the portfolio. "
        "Returns per-holding breakdown and total portfolio summary."
    )
    args_schema: Type[BaseModel] = _EmptyInput

    def _run(self) -> str:
        try:
            holdings = database.get_portfolio()

            if not holdings:
                return json.dumps({
                    "holdings": [],
                    "total_value": 0,
                    "total_cost": 0,
                    "daily_pnl": 0,
                    "message": "Portfolio is empty",
                })

            symbols = list({h["symbol"] for h in holdings})
            tickers = yf.Tickers(" ".join(symbols))

            enriched = []
            total_value = 0.0
            total_cost = 0.0
            daily_pnl = 0.0

            for h in holdings:
                sym = h["symbol"]
                try:
                    ticker = tickers.tickers[sym]
                    info = ticker.info
                    current_price = info.get("regularMarketPrice") or info.get("previousClose", 0)
                    prev_close = info.get("previousClose", current_price)
                except Exception:
                    current_price = 0
                    prev_close = 0

                position_value = current_price * h["shares"]
                position_cost = h["avg_cost"] * h["shares"]
                position_pnl = (current_price - prev_close) * h["shares"]

                total_value += position_value
                total_cost += position_cost
                daily_pnl += position_pnl

                enriched.append({
                    "symbol": sym,
                    "shares": h["shares"],
                    "avg_cost": h["avg_cost"],
                    "current_price": round(current_price, 2),
                    "position_value": round(position_value, 2),
                    "position_cost": round(position_cost, 2),
                    "unrealized_pnl": round(position_value - position_cost, 2),
                    "daily_pnl": round(position_pnl, 2),
                })

            result = {
                "holdings": enriched,
                "total_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "daily_pnl": round(daily_pnl, 2),
                "total_unrealized_pnl": round(total_value - total_cost, 2),
            }
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})
