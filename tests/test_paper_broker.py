"""Unit tests for the paper-trading engine. Pure functions → no fixtures needed."""
from __future__ import annotations

import pytest

import paper_broker as pb


def test_default_account_starts_fresh():
    a = pb.default_account()
    assert a["cash"] == pb.STARTING_CASH
    assert a["positions"] == {}
    assert a["trades"] == []
    assert a["realized"] == 0.0


def test_buy_deducts_cash_and_records_position():
    a = pb.default_account()
    a, msg = pb.buy(a, "AAPL", 10, 200.0)
    assert "Bought" in msg
    assert a["cash"] == pytest.approx(pb.STARTING_CASH - 2000.0)
    assert a["positions"]["AAPL"]["qty"] == 10
    assert a["positions"]["AAPL"]["cost_basis"] == pytest.approx(2000.0)
    assert len(a["trades"]) == 1
    assert a["trades"][0]["side"] == "BUY"


def test_buy_uppercases_symbol():
    a = pb.default_account()
    a, _ = pb.buy(a, "aapl", 1, 100.0)
    assert "AAPL" in a["positions"]


def test_buy_rejects_insufficient_cash():
    a = pb.default_account()
    a, msg = pb.buy(a, "AAPL", 10_000, 100.0)  # $1M > $100k cash
    assert "Not enough cash" in msg
    assert a["cash"] == pb.STARTING_CASH
    assert "AAPL" not in a["positions"]


def test_buy_rejects_zero_or_negative_qty():
    a = pb.default_account()
    _, msg1 = pb.buy(a, "AAPL", 0, 100.0)
    _, msg2 = pb.buy(a, "AAPL", -5, 100.0)
    assert "positive" in msg1.lower()
    assert "positive" in msg2.lower()
    assert "AAPL" not in a["positions"]


def test_buy_rejects_zero_or_negative_price():
    a = pb.default_account()
    _, msg = pb.buy(a, "AAPL", 5, 0)
    assert "positive" in msg.lower()


def test_multiple_buys_accumulate_cost_basis():
    a = pb.default_account()
    a, _ = pb.buy(a, "MSFT", 10, 100.0)  # $1000 basis
    a, _ = pb.buy(a, "MSFT", 5, 200.0)   # +$1000 basis
    pos = a["positions"]["MSFT"]
    assert pos["qty"] == 15
    assert pos["cost_basis"] == pytest.approx(2000.0)
    # avg cost = 2000/15 ≈ $133.33
    assert pos["cost_basis"] / pos["qty"] == pytest.approx(133.333, rel=1e-3)


def test_sell_realizes_gain_and_credits_cash():
    a = pb.default_account()
    a, _ = pb.buy(a, "TSLA", 10, 100.0)
    a, msg = pb.sell(a, "TSLA", 5, 150.0)
    # sold half at $150, avg cost was $100 → realized $50 * 5 = $250
    assert a["realized"] == pytest.approx(250.0)
    assert a["positions"]["TSLA"]["qty"] == 5
    assert a["positions"]["TSLA"]["cost_basis"] == pytest.approx(500.0)  # 5 * $100 avg
    assert a["cash"] == pytest.approx(pb.STARTING_CASH - 1000.0 + 750.0)
    assert "realized +$250.00" in msg


def test_sell_realizes_loss():
    a = pb.default_account()
    a, _ = pb.buy(a, "NVDA", 10, 500.0)
    a, msg = pb.sell(a, "NVDA", 10, 400.0)
    assert a["realized"] == pytest.approx(-1000.0)
    assert "NVDA" not in a["positions"]  # fully closed
    assert "realized -$1,000.00" in msg


def test_sell_closes_position_when_fully_sold():
    a = pb.default_account()
    a, _ = pb.buy(a, "AMD", 3, 100.0)
    a, _ = pb.sell(a, "AMD", 3, 120.0)
    assert "AMD" not in a["positions"]


def test_sell_rejects_more_than_held():
    a = pb.default_account()
    a, _ = pb.buy(a, "AAPL", 5, 100.0)
    _, msg = pb.sell(a, "AAPL", 10, 100.0)
    assert "Not enough shares" in msg
    assert a["positions"]["AAPL"]["qty"] == 5


def test_sell_rejects_when_no_position():
    a = pb.default_account()
    _, msg = pb.sell(a, "GOOG", 1, 100.0)
    assert "Not enough shares" in msg


def test_position_value_uses_live_prices():
    a = pb.default_account()
    a, _ = pb.buy(a, "AAPL", 10, 200.0)
    vals = pb.position_value(a, {"AAPL": 250.0})
    assert vals["AAPL"] == pytest.approx(2500.0)


def test_position_value_falls_back_to_cost_when_price_missing():
    a = pb.default_account()
    a, _ = pb.buy(a, "OBSCURE", 10, 5.0)
    vals = pb.position_value(a, {})
    # No live price → fall back to cost basis so equity doesn't NaN out.
    assert vals["OBSCURE"] == pytest.approx(50.0)


def test_total_equity_matches_cash_when_no_positions():
    a = pb.default_account()
    assert pb.total_equity(a, {}) == pb.STARTING_CASH


def test_total_equity_adds_positions_to_cash():
    a = pb.default_account()
    a, _ = pb.buy(a, "AAPL", 10, 100.0)   # $1000 out, $99k cash left
    eq = pb.total_equity(a, {"AAPL": 150.0})  # position worth $1500
    assert eq == pytest.approx(99_000 + 1500)


def test_unrealized_pnl_computes_per_symbol_gain():
    a = pb.default_account()
    a, _ = pb.buy(a, "META", 4, 250.0)  # basis $1000
    upl = pb.unrealized_pnl(a, {"META": 300.0})  # value $1200
    assert upl["META"] == pytest.approx(200.0)


def test_unrealized_pnl_skips_missing_prices():
    a = pb.default_account()
    a, _ = pb.buy(a, "META", 4, 250.0)
    upl = pb.unrealized_pnl(a, {})
    assert "META" not in upl


def test_account_summary_totals_cleanly():
    a = pb.default_account()
    a, _ = pb.buy(a, "AAPL", 10, 100.0)  # $1000 out
    a, _ = pb.buy(a, "MSFT", 5, 200.0)   # $1000 out
    s = pb.account_summary(a, {"AAPL": 150.0, "MSFT": 180.0})
    # cash: $100k - $2k = $98k. Positions: 10*150 + 5*180 = 2400
    assert s["cash"] == pytest.approx(98_000)
    assert s["positions_value"] == pytest.approx(2400)
    assert s["equity"] == pytest.approx(100_400)
    assert s["total_return"] == pytest.approx(400)
    assert s["total_return_pct"] == pytest.approx(0.004)
    assert s["n_positions"] == 2
    assert s["n_trades"] == 2
    assert s["realized"] == 0.0
    # Unrealized: (150-100)*10 + (180-200)*5 = 500 - 100 = 400
    assert s["unrealized"] == pytest.approx(400)


def test_round_trip_conserves_cash_at_flat_price():
    """Buying then selling at the same price should leave cash unchanged
    and realized P/L at zero — a nice property test."""
    a = pb.default_account()
    a, _ = pb.buy(a, "SPY", 10, 500.0)
    a, _ = pb.sell(a, "SPY", 10, 500.0)
    assert a["cash"] == pytest.approx(pb.STARTING_CASH)
    assert a["realized"] == pytest.approx(0.0)
    assert "SPY" not in a["positions"]


def test_trade_log_snapshots_cash_after_each_trade():
    a = pb.default_account()
    a, _ = pb.buy(a, "AAPL", 1, 100.0)
    a, _ = pb.buy(a, "MSFT", 1, 200.0)
    assert a["trades"][0]["cash_after"] == pytest.approx(pb.STARTING_CASH - 100)
    assert a["trades"][1]["cash_after"] == pytest.approx(pb.STARTING_CASH - 300)
