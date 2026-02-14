<div align="center">

# StockBot

**AI-Powered Stock Market Assistant**

Real-time market data, technical analysis, news aggregation, and actionable AI insights — delivered through a production-grade API and built-in web dashboard.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-FF6B6B)](https://crewai.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Quick Start](#quick-start) | [Web Dashboard](#web-dashboard) | [API Reference](#api-endpoints) | [Deployment](#deployment-guide)

</div>

---

> **Disclaimer**: This is an educational project for learning and demonstration purposes. It is **not financial advice**. See the full [Disclaimer](#disclaimer) section before using.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Web Dashboard](#web-dashboard)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Deployment Guide](#deployment-guide)
- [Project Structure](#project-structure)
- [Technical Indicators](#technical-indicators)
- [Roadmap](#roadmap)
- [Disclaimer](#disclaimer)
- [About the Author](#about-the-author)
- [License](#license)

---

## Overview

StockBot is a self-hosted stock market assistant that combines real-time market data with AI-powered analysis. It fetches live prices, computes technical indicators, gathers news headlines, and uses a Large Language Model to interpret everything into clear, actionable insights.

**How it works:**

1. **You ask** — "Analyze QQQ" (via API or web dashboard)
2. **StockBot fetches** — Real-time price, 11 technical indicators, and latest news from Yahoo Finance
3. **AI interprets** — A CrewAI agent reads all the data and produces a human-readable analysis
4. **You receive** — Structured JSON with verified market data and an AI-generated buy/hold/sell recommendation

The numbers are always real. The AI only interprets — it never fabricates data.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Stock Analysis** | Deep-dive into any ticker — price, technicals, news, and AI recommendation |
| **Morning Briefing** | AI-generated summary for your entire watchlist in a single request |
| **Portfolio Tracking** | Track holdings with real-time P&L calculations and AI commentary |
| **Price Alerts** | Set price targets (above/below) and check for triggered conditions |
| **Quick Quote** | Instant data endpoint — price, indicators, and news with zero AI latency |
| **Web Dashboard** | Built-in dark-themed UI with watchlist, analysis, portfolio, alerts, and briefing tabs |
| **Multi-LLM Support** | Switch between Ollama, Google Gemini, OpenAI, or Anthropic with a single environment variable |
| **Data-First Design** | All market data is fetched from real APIs — AI interprets but never generates numbers |

---

## Web Dashboard

StockBot ships with a built-in web dashboard. No separate frontend build or installation required — open your browser and navigate to the server URL.

```
http://your-server:5050
```

### Dashboard Tabs

| Tab | Description |
|-----|-------------|
| **Dashboard** | Live watchlist cards with prices, daily change, and signal summaries. Click any card to trigger a full AI analysis. Add or remove symbols directly from the interface. |
| **Analysis** | Enter any ticker symbol for a comprehensive AI-powered analysis — technicals grid, recent news, and a color-coded BUY / HOLD / SELL recommendation badge. |
| **Portfolio** | Manage holdings with real-time P&L tracking. Color-coded gains and losses. AI-generated portfolio summary on each refresh. |
| **Alerts** | Create price alerts with above/below conditions. View active alerts and check for triggered conditions with a single click. |
| **Briefing** | Generate an AI morning briefing covering your entire watchlist — individual symbol cards plus a comprehensive market summary. |

### Dashboard Highlights

- **Dark theme** with glass-morphism design for comfortable extended use
- **Instant quotes** via the Quote button (no AI wait time)
- **Keyboard shortcuts** — `Enter` for quick quote, `Shift+Enter` for AI analysis
- **Live health indicator** — displays LLM provider, model name, and connection status
- **Toast notifications** — real-time success and error feedback
- **Responsive layout** — optimized for desktop, tablet, and mobile viewports
- **Zero build step** — pure HTML, JavaScript, and CSS served directly by FastAPI

### Frontend Stack

| Technology | Purpose |
|-----------|---------|
| Tailwind CSS (CDN) | Utility-first styling framework |
| Vanilla JavaScript | API integration, DOM manipulation, state management |
| marked.js (CDN) | Markdown-to-HTML rendering for AI responses |
| FastAPI StaticFiles | Served from the same container — no additional infrastructure |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│               Web Dashboard  |  REST API  |  cURL                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    FastAPI + Gunicorn                            │
│              (CORS, Static Files, Health Checks)                 │
└──────────┬───────────────────────────────────────┬───────────────┘
           │                                       │
┌──────────▼───────────────┐         ┌─────────────▼───────────────┐
│      Data Layer          │         │        AI Layer             │
│      (Direct Fetch)      │         │        (CrewAI)             │
│                          │         │                             │
│  ┌────────────────────┐  │         │  ┌────────────────────────┐ │
│  │ yfinance           │  │         │  │ Strategy Reporter      │ │
│  │ - Prices & Volume  │  │         │  │ Agent                  │ │
│  │ - Company Info     │  │         │  │                        │ │
│  │ - News Headlines   │  │         │  │ Interprets real data   │ │
│  └────────────────────┘  │         │  │ and produces analysis  │ │
│                          │         │  │ with recommendations   │ │
│  ┌────────────────────┐  │         │  └───────────┬────────────┘ │
│  │ ta (Python)        │  │         │              │              │
│  │ - RSI, MACD        │  │         │  ┌───────────▼────────────┐ │
│  │ - SMA, Bollinger   │  │         │  │ LLM Provider           │ │
│  │ - ATR              │  │         │  │                        │ │
│  └────────────────────┘  │         │  │ - Ollama (local)       │ │
│                          │         │  │ - Google Gemini        │ │
│  ┌────────────────────┐  │         │  │ - OpenAI               │ │
│  │ SQLite (WAL)       │  │         │  │ - Anthropic            │ │
│  │ - Portfolio        │  │         │  └────────────────────────┘ │
│  │ - Watchlist        │  │         │                             │
│  │ - Alerts           │  │         │                             │
│  └────────────────────┘  │         │                             │
└──────────────────────────┘         └─────────────────────────────┘
```

### Data-First Design

StockBot follows a **data-first architecture** — all market data is fetched directly from external APIs and computed locally. The AI layer receives verified data and is responsible only for interpretation.

```
Step 1  Fetch real-time data        yfinance (prices, volume, 52-week range)
Step 2  Compute technical indicators    ta library (RSI, MACD, SMA, Bollinger, ATR)
Step 3  Gather news headlines       yfinance news feed (real headlines with sources)
Step 4  AI interpretation           LLM reads verified data and writes analysis
Step 5  Structured response         JSON with raw data fields + AI summary
```

**Why this matters:** The numeric fields in every response (`price`, `change_pct`, `technicals`) are sourced directly from market APIs and are always accurate. The AI provides interpretation and recommendations in separate fields (`ai_analysis`, `ai_recommendation`). Users can trust the data independently of the AI output.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | FastAPI + Gunicorn | Production-grade async API with OpenAPI documentation |
| **AI Agents** | CrewAI + LiteLLM | Multi-agent orchestration with provider-agnostic LLM support |
| **Market Data** | yfinance | Real-time prices, company fundamentals, and news |
| **Technical Analysis** | ta (Python) | RSI, MACD, SMA, Bollinger Bands, ATR computation |
| **Database** | SQLite (WAL mode) | Persistent storage for portfolio, watchlist, and alerts |
| **Web Dashboard** | HTML + Tailwind CSS + JavaScript | Built-in UI served by FastAPI — zero build tooling |
| **Containerization** | Docker Compose | Single-command deployment with volume persistence |
| **Reverse Proxy** | Caddy (optional) | Auto-HTTPS with Let's Encrypt |

---

## Quick Start

Get StockBot running locally in under 2 minutes. No Docker required.

### Prerequisites

- Python 3.11+
- One of the following LLM providers:
  - **Ollama** running locally ([install guide](https://ollama.com/download))
  - **Google Gemini** API key ([get one free](https://aistudio.google.com/apikey))
  - **OpenAI** or **Anthropic** API key

### Installation

```bash
# Clone the repository
git clone https://github.com/crewwithravi/stockbot.git
cd stockbot

# Install dependencies
pip install -r requirements.txt
```

### Start the Server

**Option A — Google Gemini (easiest, no GPU required):**
```bash
LLM_PROVIDER=gemini \
LLM_MODEL=gemini-2.0-flash \
GEMINI_API_KEY=your-api-key \
STOCKBOT_DB_PATH=/tmp/stockbot.db \
PYTHONPATH=app \
uvicorn main:app --host 0.0.0.0 --port 5050
```

**Option B — Ollama (free, local GPU):**
```bash
# Ensure Ollama is running: ollama pull qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434 \
STOCKBOT_DB_PATH=/tmp/stockbot.db \
PYTHONPATH=app \
uvicorn main:app --host 0.0.0.0 --port 5050
```

### Verify

```bash
# Health check
curl http://localhost:5050/health

# Quick quote (instant, no AI)
curl http://localhost:5050/quote/AAPL

# Full AI analysis (15-60 seconds depending on LLM)
curl http://localhost:5050/analyze/QQQ

# Open the dashboard
open http://localhost:5050
```

---

## API Endpoints

### Data Endpoints (Instant Response)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web dashboard |
| `GET` | `/health` | Health check — LLM connection status and provider info |
| `GET` | `/quote/{symbol}` | Quick quote — price, technicals, news (no AI, instant) |

### AI-Powered Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analyze/{symbol}` | Full AI analysis with buy/hold/sell recommendation |
| `POST` | `/briefing` | Morning briefing for all watchlist symbols |
| `GET` | `/portfolio` | Portfolio overview with AI-generated summary |

### Management Endpoints (CRUD)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/portfolio` | Add a holding (`symbol`, `shares`, `avg_cost`) |
| `DELETE` | `/portfolio/{symbol}` | Remove a holding |
| `GET` | `/watchlist` | List watchlist symbols |
| `POST` | `/watchlist` | Add symbol to watchlist |
| `DELETE` | `/watchlist/{symbol}` | Remove from watchlist |
| `GET` | `/alerts` | List active price alerts |
| `POST` | `/alerts` | Create a price alert (`above` / `below`) |
| `POST` | `/check-alerts` | Evaluate active alerts against current prices |

Interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Usage Examples

### Quick Quote (Instant)

```bash
curl http://localhost:5050/quote/AAPL
```

```json
{
  "symbol": "AAPL",
  "price": 227.63,
  "change_pct": -1.02,
  "technicals": {
    "rsi_14": 52.31,
    "macd": 1.24,
    "sma_20": 224.85,
    "sma_50": 220.12,
    "sma_200": 198.45,
    "bollinger_upper": 235.20,
    "bollinger_lower": 214.50,
    "atr_14": 4.82
  },
  "signal_summary": "RSI(52.31) is neutral; MACD is above signal line (bullish)",
  "news": [
    {
      "title": "Apple Reports Record Q1 Revenue",
      "publisher": "Reuters",
      "link": "https://...",
      "publish_time": "2026-02-12T14:30:00Z"
    }
  ]
}
```

### AI Stock Analysis

```bash
curl http://localhost:5050/analyze/QQQ
```

Response includes:
- `price`, `change_pct` — real-time from Yahoo Finance
- `technicals` — 11 indicators computed from historical data
- `news` — actual headlines with publisher and links
- `ai_analysis` — LLM-generated interpretation (markdown)
- `ai_recommendation` — BUY, HOLD, or SELL with reasoning

### Morning Briefing

```bash
curl -X POST http://localhost:5050/briefing
```

Returns an AI-written briefing for your entire watchlist (default: SLV, QQQ) with per-symbol analysis and a market overview.

### Portfolio Management

```bash
# Add a holding
curl -X POST http://localhost:5050/portfolio \
  -H 'Content-Type: application/json' \
  -d '{"symbol": "QQQ", "shares": 10, "avg_cost": 480.50}'

# View portfolio with AI summary
curl http://localhost:5050/portfolio

# Remove a holding
curl -X DELETE http://localhost:5050/portfolio/QQQ
```

### Price Alerts

```bash
# Create alert: trigger when QQQ exceeds $550
curl -X POST http://localhost:5050/alerts \
  -H 'Content-Type: application/json' \
  -d '{"symbol": "QQQ", "condition": "above", "price": 550}'

# Check all active alerts against current prices
curl -X POST http://localhost:5050/check-alerts
```

---

## Configuration

All configuration is managed through environment variables in the `.env` file:

```env
# ── LLM Provider ──────────────────────────────────────
# Options: ollama, gemini, openai, anthropic
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b

# ── Ollama (only if LLM_PROVIDER=ollama) ──────────────
OLLAMA_BASE_URL=http://host.docker.internal:11434

# ── Google Gemini (only if LLM_PROVIDER=gemini) ───────
# GEMINI_API_KEY=your-api-key

# ── OpenAI (only if LLM_PROVIDER=openai) ──────────────
# OPENAI_API_KEY=your-api-key

# ── Anthropic (only if LLM_PROVIDER=anthropic) ────────
# ANTHROPIC_API_KEY=your-api-key

# ── Application ───────────────────────────────────────
APP_PORT=5050
```

### Supported LLM Providers

| Provider | Model Examples | GPU Required | Cost |
|----------|---------------|:------------:|------|
| **Ollama** | `qwen2.5:7b`, `llama3.1:8b`, `mistral:7b` | Yes (local) | Free |
| **Google Gemini** | `gemini-2.0-flash`, `gemini-3-pro-preview` | No | Pay-per-token |
| **OpenAI** | `gpt-4o-mini`, `gpt-4o` | No | Pay-per-token |
| **Anthropic** | `claude-sonnet-4-20250514` | No | Pay-per-token |

Switching providers requires changing `LLM_PROVIDER` and `LLM_MODEL` in your `.env` file followed by a container restart. No code changes are necessary.

---

## Deployment Guide

### Option 1: Docker Compose (Recommended)

For servers with Ollama already installed on the host.

```bash
# Clone and configure
git clone https://github.com/crewwithravi/stockbot.git
cd stockbot
cp .env.production .env

# Edit .env — set your LLM provider and keys
nano .env

# Build and start
docker compose up -d --build

# Verify
curl http://localhost:5050/health
```

### Option 2: Docker + Ollama Container (Full Self-Hosted)

For fresh servers where Ollama is not yet installed.

```bash
# Clone and configure
git clone https://github.com/crewwithravi/stockbot.git
cd stockbot
cp .env.production .env

# Set Ollama URL for container networking
# In .env: OLLAMA_BASE_URL=http://ollama:11434

# Start API + Ollama with GPU passthrough
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d --build

# Pull a model (first time only)
docker exec stockbot-ollama ollama pull qwen2.5:7b

# Verify
curl http://localhost:5050/health
```

### Option 3: Cloud LLM (No GPU Required)

For servers without a GPU, or when using a cloud-based LLM provider.

```bash
# Clone and configure
git clone https://github.com/crewwithravi/stockbot.git
cd stockbot
cp .env.example .env

# Edit .env — example for Gemini:
#   LLM_PROVIDER=gemini
#   LLM_MODEL=gemini-2.0-flash
#   GEMINI_API_KEY=your-api-key

# Start (no Ollama needed)
docker compose up -d --build

# Verify
curl http://localhost:5050/health
```

### Optional: Caddy Reverse Proxy (HTTPS)

For production deployments with a custom domain and automatic SSL.

```bash
# Start with Caddy overlay
docker compose -f docker-compose.yml -f docker-compose.caddy.yml up -d --build
```

Edit the `Caddyfile` to set your domain. Caddy automatically provisions Let's Encrypt certificates.

### Production Components

| Component | Configuration | Purpose |
|-----------|--------------|---------|
| **Gunicorn** | 2 workers, 300s timeout | Production WSGI server for long-running AI requests |
| **SQLite** | WAL mode, Docker volume | Persistent storage that survives restarts and rebuilds |
| **Log Rotation** | 10 MB max, 3 files | Prevents disk exhaustion on long-running deployments |
| **Health Checks** | 30s interval, 3 retries | Docker-native health monitoring at `/health` |
| **Auto-Restart** | `unless-stopped` policy | Automatic recovery from crashes |
| **Non-Root User** | `stockbot` user | Container runs with least-privilege security |
| **CORS** | All origins enabled | Allows frontend clients from any domain |
| **Host Gateway** | `extra_hosts` mapping | Enables container-to-host communication on Linux |

### Post-Deployment Checklist

- [ ] `curl http://your-server:5050/health` returns `"status": "ok"`
- [ ] `curl http://your-server:5050/quote/QQQ` returns real-time price data
- [ ] `curl http://your-server:5050/analyze/QQQ` returns AI analysis
- [ ] `http://your-server:5050` loads the web dashboard in a browser
- [ ] `docker compose logs -f stockbot-api` shows clean startup logs
- [ ] Data persists across restarts: `docker compose restart`, verify `/watchlist` retains symbols

### Updating

```bash
cd stockbot
git pull
docker compose up -d --build
```

Portfolio, watchlist, and alert data is stored in a Docker volume and is preserved across image rebuilds.

---

## Project Structure

```
stockbot/
├── app/
│   ├── __init__.py                # Package initializer
│   ├── main.py                    # FastAPI application — routes, middleware, data-first logic
│   ├── agents.py                  # CrewAI agent definitions, multi-provider LLM configuration
│   ├── tools.py                   # Custom tools — stock data, technicals, news, portfolio
│   ├── models.py                  # Pydantic request/response schemas with validation
│   └── database.py                # SQLite persistence — portfolio, watchlist, alerts CRUD
├── static/
│   ├── index.html                 # Web dashboard — Tailwind CSS, dark theme, responsive
│   └── app.js                     # Client-side logic — API integration, tabs, rendering
├── requirements.txt               # Python dependencies (pinned ranges)
├── .env.example                   # Environment template for local development
├── .env.production                # Environment template for Docker deployment
├── .gitignore                     # Excludes .env, *.db, __pycache__, .venv
├── Dockerfile                     # Multi-stage production image with Gunicorn
├── docker-compose.yml             # Core service — API on port 5050
├── docker-compose.ollama.yml      # Optional overlay — Ollama container with GPU
├── docker-compose.caddy.yml       # Optional overlay — Caddy reverse proxy with HTTPS
├── Caddyfile                      # Caddy configuration for reverse proxy
└── README.md                      # Project documentation
```

---

## Technical Indicators

StockBot computes the following indicators from historical OHLCV data:

| Indicator | Parameters | Signal |
|-----------|-----------|--------|
| **RSI** | 14-period | Overbought (> 70), Oversold (< 30), Neutral (30-70) |
| **MACD** | 12, 26, 9 | Bullish when MACD crosses above signal line |
| **MACD Histogram** | 12, 26, 9 | Momentum strength and direction |
| **SMA 20** | 20-day | Short-term trend direction |
| **SMA 50** | 50-day | Medium-term trend direction |
| **SMA 200** | 200-day | Long-term trend direction |
| **Golden/Death Cross** | SMA 50 vs SMA 200 | Golden cross (bullish), Death cross (bearish) |
| **Bollinger Bands** | 20-period, 2 std dev | Price at upper band (overextended), lower band (oversold) |
| **ATR** | 14-period | Average daily price range — measures volatility |

The `signal_summary` field provides a plain-English interpretation:

> *"RSI(47.06) is neutral; MACD is below signal line (bearish); Golden cross: SMA50 above SMA200 (bullish)"*

---

## Roadmap

- [x] Core API — multi-agent pipeline, REST endpoints, multi-LLM provider support
- [x] Portfolio & Alerts — holdings tracking, price alerts, watchlist management
- [x] Web Dashboard — responsive UI with watchlist, analysis, portfolio, alerts, and briefing
- [ ] Scheduled Scanning — automatic alert checking on configurable intervals
- [ ] Push Notifications — Telegram and n8n integration for triggered alerts
- [ ] Historical Backtesting — evaluate signal accuracy against historical data
- [ ] Charting — interactive price and indicator charts in the dashboard

---

## Disclaimer

**This project is for educational and demonstration purposes only.**

- The author is **not a financial advisor**, licensed broker, or registered investment professional.
- StockBot is a **beta-stage experimental tool** built to explore multi-agent AI systems and financial data APIs.
- AI-generated analysis, recommendations (BUY / HOLD / SELL), and commentary are **produced by a language model** and must **never** be interpreted as financial advice.
- Market data is sourced from Yahoo Finance via the yfinance library and may be **delayed, incomplete, or inaccurate**. Always verify data with your licensed broker or financial institution.
- Technical indicators are mathematical computations based on historical price data. They **do not predict future price movements**.
- **Do not make investment decisions based solely on this tool.** Conduct your own due diligence, consult a qualified financial advisor, and fully understand the risks before committing capital.
- The author assumes **no responsibility** for financial losses, missed opportunities, or damages of any kind resulting from the use of this software.
- Securities markets involve **substantial risk**, including the potential loss of your entire investment. Past performance is not indicative of future results.
- By using StockBot, you acknowledge these risks and accept full responsibility for your own financial decisions.

**This is a technology demonstration — not investment software. Use at your own risk.**

---

## About the Author

**Ravi D** — Principal Application Engineer specializing in enterprise-grade software development within the financial services industry.

### Professional Background

- **10+ years** of experience in application development, platform engineering, and systems architecture across banking and financial services
- **Principal Application Engineer** — designing and building high-availability, mission-critical applications for large-scale financial platforms
- Deep expertise in **DevOps practices**, **CI/CD pipeline design**, **Kubernetes orchestration**, and **cloud-native architectures**
- **AWS Certified** — hands-on experience with production workloads on AWS, including ECS, EKS, Lambda, and infrastructure-as-code
- Proficient in **containerization** (Docker, Kubernetes), **infrastructure automation** (Terraform, Ansible), and **observability** (Prometheus, Grafana, ELK)

### Academic

- Currently pursuing a **Master's degree in Data Science**, with a focus on applied machine learning, statistical modeling, and AI systems
- StockBot was developed as a personal research project during this program — exploring multi-agent AI architectures, real-time data pipelines, and production API design

### About This Project

StockBot is an independent, personal project built entirely on the author's own time using publicly available tools, libraries, and data sources. It is **not affiliated with, endorsed by, or connected to any employer** or financial institution.

**Architecture & Design** — Ravi D
**Development** — Ravi D, with AI-assisted coding

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Built with [CrewAI](https://crewai.com) | [FastAPI](https://fastapi.tiangolo.com) | [yfinance](https://github.com/ranaroussi/yfinance)**

</div>
