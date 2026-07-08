"""store.py — local persistence for Aurora Portfolio Lab.

A tiny storage abstraction so the watchlist, paper wallet, and trade log
survive a browser refresh (Streamlit's ``session_state`` does not). Today it's
backed by SQLite in a single ``aurora.db`` file next to the app; every function
is keyed by ``user_id`` so the exact same surface could later be re-pointed at
Postgres / Supabase / a real auth'd backend without touching the callers.

Design notes for the owner (this is a learning repo):
- **Zero Streamlit imports.** Like ``paper_broker.py`` and ``finance_metrics``,
  this stays framework-free so it's trivial to unit-test or reuse.
- **One connection per call.** SQLite handles its own file locking, and a fresh
  connection per call sidesteps Streamlit's re-run / multi-session threading
  entirely. It's plenty fast for a portfolio piece.
- **Paper money is dollar-denominated here.** ``place_paper_trade`` takes an
  *amount in USD* (buy $500 of AAPL) rather than a share count — that's the
  mental model the watchlist ticket and wallet "Swap" use. Shares are derived
  as ``amount_usd / price``. (The richer share-based game still lives in
  ``paper_broker.py``; this is the persisted, simpler ledger.)
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3

# The database lives beside the app so a clone "just works" with no config.
# It's git-ignored — it's per-user runtime state, not source.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora.db")

# Every account starts with this much fake money. Small round number so the
# paper game feels approachable (vs. the $100k share-game in paper_broker.py).
STARTING_CASH: float = 10_000.0

DEFAULT_USER = "local"


def _connect() -> sqlite3.Connection:
    """Open a fresh connection. ``check_same_thread=False`` because Streamlit
    may service reruns on different threads; a per-call connection keeps that
    safe without a shared global. Rows come back as dict-friendly ``Row``s."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    """Create the schema if it's missing. Runs once on import — cheap and
    idempotent thanks to ``IF NOT EXISTS``."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                user_id TEXT,
                symbol  TEXT,
                PRIMARY KEY (user_id, symbol)
            );

            CREATE TABLE IF NOT EXISTS paper_account (
                user_id TEXT PRIMARY KEY,
                cash    REAL DEFAULT 10000
            );

            CREATE TABLE IF NOT EXISTS positions (
                user_id TEXT,
                symbol  TEXT,
                qty     REAL,
                PRIMARY KEY (user_id, symbol)
            );

            CREATE TABLE IF NOT EXISTS trades (
                user_id    TEXT,
                ts         TEXT,
                side       TEXT,
                symbol     TEXT,
                amount_usd REAL,
                price      REAL
            );
            """
        )


# Initialize the schema at import time so callers never have to think about it.
_init_db()


def _norm_symbol(symbol: str) -> str:
    """Uppercase + trim so 'aapl ' and 'AAPL' are the same watchlist row."""
    return str(symbol).upper().strip()


# ---------------------------------------------------------------------------
# WATCHLIST
# ---------------------------------------------------------------------------
def get_watchlist(user_id: str = DEFAULT_USER) -> list[str]:
    """Return the user's starred symbols, alphabetically for a stable order."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT symbol FROM watchlist WHERE user_id = ? ORDER BY symbol",
            (user_id,),
        ).fetchall()
    return [r["symbol"] for r in rows]


def add_star(user_id: str = DEFAULT_USER, symbol: str = "") -> None:
    """Star a symbol. ``INSERT OR IGNORE`` makes re-starring a no-op."""
    sym = _norm_symbol(symbol)
    if not sym:
        return
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, symbol) VALUES (?, ?)",
            (user_id, sym),
        )


def remove_star(user_id: str = DEFAULT_USER, symbol: str = "") -> None:
    """Un-star a symbol. Silently does nothing if it wasn't starred."""
    sym = _norm_symbol(symbol)
    with _connect() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
            (user_id, sym),
        )


# ---------------------------------------------------------------------------
# PAPER ACCOUNT (dollar-denominated ledger)
# ---------------------------------------------------------------------------
def _ensure_account(conn: sqlite3.Connection, user_id: str) -> None:
    """Create the account row with the starting cash if it doesn't exist yet."""
    conn.execute(
        "INSERT OR IGNORE INTO paper_account (user_id, cash) VALUES (?, ?)",
        (user_id, STARTING_CASH),
    )


def get_account(user_id: str = DEFAULT_USER) -> dict:
    """Return ``{"cash": float, "positions": {symbol: qty}}``.

    Creates the account (seeded with ``STARTING_CASH`` paper USD) on first
    access so the wallet always has something to show."""
    with _connect() as conn:
        _ensure_account(conn, user_id)
        cash_row = conn.execute(
            "SELECT cash FROM paper_account WHERE user_id = ?", (user_id,)
        ).fetchone()
        pos_rows = conn.execute(
            "SELECT symbol, qty FROM positions WHERE user_id = ? AND qty > 0 ORDER BY symbol",
            (user_id,),
        ).fetchall()
    return {
        "cash": float(cash_row["cash"]) if cash_row else STARTING_CASH,
        "positions": {r["symbol"]: float(r["qty"]) for r in pos_rows},
    }


def place_paper_trade(
    user_id: str = DEFAULT_USER,
    side: str = "BUY",
    symbol: str = "",
    amount_usd: float = 0.0,
    price: float = 0.0,
) -> dict:
    """Buy or sell ``amount_usd`` worth of ``symbol`` at ``price``.

    Shares are derived as ``amount_usd / price`` (dollar-denominated trading).
    A BUY is rejected when it exceeds available cash. A SELL is clamped to the
    shares actually held so the ledger can never go short.

    Returns ``{"ok": bool, "message": str, "cash": float,
    "positions": {...}}`` — ``ok=False`` leaves the account untouched."""
    sym = _norm_symbol(symbol)
    side = str(side).upper().strip()
    amount_usd = float(amount_usd)
    price = float(price)

    if not sym:
        return {"ok": False, "message": "Symbol required.", **get_account(user_id)}
    if side not in ("BUY", "SELL"):
        return {"ok": False, "message": "Side must be BUY or SELL.", **get_account(user_id)}
    if amount_usd <= 0:
        return {"ok": False, "message": "Amount must be positive.", **get_account(user_id)}
    if price <= 0:
        return {"ok": False, "message": "Need a live price to trade.", **get_account(user_id)}

    # Everything happens on ONE connection — no nested get_account() while a
    # write transaction is open (that self-deadlocks SQLite with "database is
    # locked"). We read the account back once, after the block has committed.
    with _connect() as conn:
        _ensure_account(conn, user_id)
        cash = float(
            conn.execute(
                "SELECT cash FROM paper_account WHERE user_id = ?", (user_id,)
            ).fetchone()["cash"]
        )
        held_row = conn.execute(
            "SELECT qty FROM positions WHERE user_id = ? AND symbol = ?",
            (user_id, sym),
        ).fetchone()
        held = float(held_row["qty"]) if held_row else 0.0

        # Validate first; a rejection leaves the account entirely untouched.
        if side == "BUY" and amount_usd > cash + 1e-6:
            reject = f"Not enough cash — need ${amount_usd:,.2f}, have ${cash:,.2f}."
        elif side == "SELL" and held <= 0:
            reject = f"No {sym} shares to sell."
        else:
            reject = None

        if reject is None:
            if side == "BUY":
                qty = amount_usd / price
                new_cash = cash - amount_usd
                new_qty = held + qty
                traded_usd = amount_usd
            else:  # SELL — clamp to shares held so we never go short.
                qty = min(amount_usd / price, held)
                traded_usd = qty * price
                new_cash = cash + traded_usd
                new_qty = held - qty

            conn.execute(
                "UPDATE paper_account SET cash = ? WHERE user_id = ?",
                (new_cash, user_id),
            )
            if new_qty > 1e-9:
                conn.execute(
                    "INSERT INTO positions (user_id, symbol, qty) VALUES (?, ?, ?) "
                    "ON CONFLICT(user_id, symbol) DO UPDATE SET qty = excluded.qty",
                    (user_id, sym, new_qty),
                )
            else:
                # Fully closed out — drop the row so it doesn't clutter the wallet.
                conn.execute(
                    "DELETE FROM positions WHERE user_id = ? AND symbol = ?",
                    (user_id, sym),
                )
            conn.execute(
                "INSERT INTO trades (user_id, ts, side, symbol, amount_usd, price) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, _now_iso(), side, sym, traded_usd, price),
            )

    account = get_account(user_id)  # single fresh read, after commit
    if reject is not None:
        return {"ok": False, "message": reject, **account}

    verb = "Bought" if side == "BUY" else "Sold"
    shares = traded_usd / price if price else 0.0
    return {
        "ok": True,
        "message": f"{verb} ${traded_usd:,.2f} of {sym} ({shares:.4f} sh @ ${price:,.2f}).",
        **account,
    }


def get_trades(user_id: str = DEFAULT_USER, limit: int = 50) -> list[dict]:
    """Most-recent-first trade log for the ledger. Each row is a plain dict:
    ``{ts, side, symbol, amount_usd, price}``."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ts, side, symbol, amount_usd, price FROM trades "
            "WHERE user_id = ? ORDER BY ts DESC, rowid DESC LIMIT ?",
            (user_id, int(limit)),
        ).fetchall()
    return [dict(r) for r in rows]


def _now_iso() -> str:
    """Second-resolution ISO timestamp for trade rows."""
    return dt.datetime.now().replace(microsecond=0).isoformat()
