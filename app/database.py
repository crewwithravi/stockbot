import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.environ.get("STOCKBOT_DB_PATH", "/app/data/stockbot.db")

DEFAULT_WATCHLIST = ["SLV", "QQQ"]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_cost REAL NOT NULL,
                added_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                added_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                condition TEXT NOT NULL CHECK(condition IN ('above', 'below')),
                price REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        # Seed default watchlist
        for symbol in DEFAULT_WATCHLIST:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)",
                (symbol,),
            )
        conn.commit()
    finally:
        conn.close()


# ── Portfolio CRUD ──────────────────────────────────────────────


def get_portfolio() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM portfolio ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_holding(symbol: str, shares: float, avg_cost: float) -> dict:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO portfolio (symbol, shares, avg_cost) VALUES (?, ?, ?)",
            (symbol.upper(), shares, avg_cost),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM portfolio WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def remove_holding(symbol: str) -> int:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM portfolio WHERE symbol = ?", (symbol.upper(),)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ── Watchlist CRUD ──────────────────────────────────────────────


def get_watchlist() -> list[str]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT symbol FROM watchlist ORDER BY added_at").fetchall()
        return [r["symbol"] for r in rows]
    finally:
        conn.close()


def add_to_watchlist(symbol: str) -> bool:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)",
            (symbol.upper(),),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def remove_from_watchlist(symbol: str) -> int:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ── Alerts CRUD ─────────────────────────────────────────────────


def get_alerts(active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    try:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE active = 1 ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_alert(symbol: str, condition: str, price: float) -> dict:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO alerts (symbol, condition, price) VALUES (?, ?, ?)",
            (symbol.upper(), condition, price),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def deactivate_alert(alert_id: int) -> int:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "UPDATE alerts SET active = 0 WHERE id = ? AND active = 1",
            (alert_id,),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
