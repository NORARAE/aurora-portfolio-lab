"""Paper-trading account for Aurora Portfolio Lab.

Pure functions over a plain-dict account state. Zero Streamlit imports so the
game logic is easy to unit-test in isolation. The dashboard keeps one account
in `st.session_state["paper"]` per browser session; the account can also be
serialized to JSON and re-loaded so a visitor can persist their game.

Design decisions:
- Long-only for v1 (no shorting). Simpler mental model; matches how a
  beginner-friendly paper-trading app usually starts.
- Average-cost basis on partial sells — the industry-standard tax lot
  approach for casual retail dashboards. FIFO/LIFO are future work.
- Cash is always tracked exactly; positions store cost_basis in dollars
  so avg cost derives cleanly even after fractional buys.
"""
from __future__ import annotations

import datetime as dt
from typing import TypedDict

STARTING_CASH: float = 100_000.0


class Position(TypedDict):
    qty: float          # total shares held (long only, so always >= 0)
    cost_basis: float   # total dollars spent to acquire the current qty


class Trade(TypedDict):
    ts: str             # ISO timestamp when the trade cleared
    side: str           # "BUY" or "SELL"
    symbol: str
    qty: float
    price: float
    total: float        # qty * price (cash out on BUY, cash in on SELL)
    cash_after: float   # snapshot of account cash right after the trade
    realized: float     # $ realized P/L on this trade (0 for BUY)


def default_account() -> dict:
    """Fresh account: $100k cash, no positions, no trade history."""
    return {
        "cash": STARTING_CASH,
        "positions": {},
        "trades": [],
        "realized": 0.0,
        "created": dt.datetime.now().replace(microsecond=0).isoformat(),
    }


def _now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def buy(account: dict, symbol: str, qty: float, price: float) -> tuple[dict, str]:
    """Buy `qty` shares of `symbol` at `price`. Returns (account, message).
    On failure the account is returned unchanged and message explains why."""
    symbol = str(symbol).upper().strip()
    if not symbol:
        return account, "Symbol required."
    if qty <= 0:
        return account, "Quantity must be positive."
    if price <= 0:
        return account, "Price must be positive."
    total = qty * price
    if total > account["cash"] + 1e-6:
        return account, (
            f"Not enough cash — need ${total:,.2f}, have ${account['cash']:,.2f}."
        )
    account["cash"] -= total
    pos = account["positions"].get(symbol) or {"qty": 0.0, "cost_basis": 0.0}
    pos["qty"] += qty
    pos["cost_basis"] += total
    account["positions"][symbol] = pos
    account["trades"].append({
        "ts": _now_iso(),
        "side": "BUY",
        "symbol": symbol,
        "qty": float(qty),
        "price": float(price),
        "total": float(total),
        "cash_after": float(account["cash"]),
        "realized": 0.0,
    })
    return account, f"Bought {qty:g} {symbol} @ ${price:,.2f}"


def sell(account: dict, symbol: str, qty: float, price: float) -> tuple[dict, str]:
    """Sell `qty` shares. Uses average-cost basis for realized P/L."""
    symbol = str(symbol).upper().strip()
    if not symbol:
        return account, "Symbol required."
    if qty <= 0:
        return account, "Quantity must be positive."
    if price <= 0:
        return account, "Price must be positive."
    pos = account["positions"].get(symbol)
    if not pos or pos["qty"] < qty - 1e-9:
        held = pos["qty"] if pos else 0.0
        return account, f"Not enough shares — want to sell {qty:g}, have {held:g}."
    avg_cost = (pos["cost_basis"] / pos["qty"]) if pos["qty"] else 0.0
    proceeds = qty * price
    realized = (price - avg_cost) * qty
    # Reduce cost_basis proportionally so remaining shares keep their avg cost.
    pos["qty"] -= qty
    pos["cost_basis"] = pos["qty"] * avg_cost
    if pos["qty"] < 1e-9:
        del account["positions"][symbol]
    else:
        account["positions"][symbol] = pos
    account["cash"] += proceeds
    account["realized"] += realized
    account["trades"].append({
        "ts": _now_iso(),
        "side": "SELL",
        "symbol": symbol,
        "qty": float(qty),
        "price": float(price),
        "total": float(proceeds),
        "cash_after": float(account["cash"]),
        "realized": float(realized),
    })
    # Format sign outside the currency to avoid "$-1,000.00".
    realized_str = f"+${realized:,.2f}" if realized >= 0 else f"-${abs(realized):,.2f}"
    return account, f"Sold {qty:g} {symbol} @ ${price:,.2f} · realized {realized_str}"


def position_value(account: dict, prices: dict[str, float]) -> dict[str, float]:
    """symbol -> current market value (qty * current price). Falls back to
    cost basis when a price is missing so total_equity never crashes."""
    out: dict[str, float] = {}
    for s, p in account["positions"].items():
        px = prices.get(s)
        if px is None:
            # No live price — value the position at its cost basis so equity
            # remains a sensible finite number instead of NaN.
            out[s] = p["cost_basis"]
        else:
            out[s] = p["qty"] * px
    return out


def total_equity(account: dict, prices: dict[str, float]) -> float:
    """Cash + market value of all open positions."""
    return float(account["cash"]) + sum(position_value(account, prices).values())


def unrealized_pnl(account: dict, prices: dict[str, float]) -> dict[str, float]:
    """symbol -> (market value − cost basis). Skips symbols missing prices."""
    out: dict[str, float] = {}
    for s, p in account["positions"].items():
        px = prices.get(s)
        if px is None:
            continue
        out[s] = p["qty"] * px - p["cost_basis"]
    return out


def account_summary(account: dict, prices: dict[str, float]) -> dict:
    """One-shot summary used by the dashboard hero row."""
    positions_val = sum(position_value(account, prices).values())
    equity = float(account["cash"]) + positions_val
    total_return = equity - STARTING_CASH
    unreal = sum(unrealized_pnl(account, prices).values())
    return {
        "cash": float(account["cash"]),
        "equity": float(equity),
        "positions_value": float(positions_val),
        "total_return": float(total_return),
        "total_return_pct": float(total_return / STARTING_CASH) if STARTING_CASH else 0.0,
        "realized": float(account["realized"]),
        "unrealized": float(unreal),
        "n_positions": len(account["positions"]),
        "n_trades": len(account["trades"]),
    }
