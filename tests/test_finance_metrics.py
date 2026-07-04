"""
Unit tests for finance_metrics.

Each function in finance_metrics is a pure function of pandas input, so we can
verify it against hand-computed values without touching Streamlit, yfinance,
or the network. The point of these tests is twofold:

  1. Catch regressions if the math ever drifts.
  2. Document the *expected* behavior in code — a reviewer can read the test
     and immediately see what the function is supposed to do.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import finance_metrics as fm

# -----------------------------------------------------------------------------
# Fixtures — small, hand-crafted series so expected values are easy to reason
# about. Real market data is too noisy to unit-test against directly.
# -----------------------------------------------------------------------------

@pytest.fixture
def rising_prices() -> pd.Series:
    """A perfectly clean 10%-per-step series: makes returns trivial to check."""
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    return pd.Series([100.0, 110.0, 121.0], index=idx)


@pytest.fixture
def flat_prices() -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.Series([100.0] * 5, index=idx)


@pytest.fixture
def peak_trough_prices() -> pd.Series:
    """Rises to 200, crashes to 100, recovers past the peak."""
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.Series([100.0, 200.0, 100.0, 150.0, 220.0], index=idx)


@pytest.fixture
def never_recovers_prices() -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    return pd.Series([100.0, 200.0, 150.0, 120.0], index=idx)


# -----------------------------------------------------------------------------
# Core return / cumulative math
# -----------------------------------------------------------------------------

class TestDailyReturns:
    def test_simple_10pct(self, rising_prices):
        out = fm.daily_returns(rising_prices)
        assert len(out) == 2
        assert out.iloc[0] == pytest.approx(0.10)
        assert out.iloc[1] == pytest.approx(0.10)

    def test_flat_series_all_zero(self, flat_prices):
        out = fm.daily_returns(flat_prices)
        assert (out == 0).all()


class TestCumulativeReturns:
    def test_growth_of_one(self, rising_prices):
        out = fm.cumulative_returns(rising_prices)
        # After two +10% days: 1.1, then 1.21
        assert out.iloc[-1] == pytest.approx(1.21)


class TestTotalReturn:
    def test_basic(self, rising_prices):
        assert fm.total_return(rising_prices) == pytest.approx(0.21)

    def test_empty_returns_zero(self):
        assert fm.total_return(pd.Series(dtype=float)) == 0.0

    def test_single_value_returns_zero(self):
        s = pd.Series([100.0], index=pd.date_range("2024-01-01", periods=1))
        assert fm.total_return(s) == 0.0


# -----------------------------------------------------------------------------
# Annualized metrics
# -----------------------------------------------------------------------------

class TestAnnualizedReturn:
    def test_geometric_annualization(self, rising_prices):
        # Two +10% days = 21% total in 2/252 of a year.
        # Annualized = 1.21 ** (252/2) - 1 — enormous number, we just check
        # it's a large positive float rather than pinning the exact value.
        out = fm.annualized_return(rising_prices)
        assert out > 100.0

    def test_empty_returns_zero(self):
        assert fm.annualized_return(pd.Series(dtype=float)) == 0.0


class TestAnnualizedVolatility:
    def test_flat_is_zero(self, flat_prices):
        assert fm.annualized_volatility(flat_prices) == pytest.approx(0.0)

    def test_positive_for_bumpy(self, peak_trough_prices):
        assert fm.annualized_volatility(peak_trough_prices) > 0

    def test_scaling_factor(self):
        # Two alternating ±10% moves — check we annualize by sqrt(252)
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        prices = pd.Series([100.0, 110.0, 99.0, 108.9, 98.01], index=idx)
        rets = fm.daily_returns(prices)
        expected = rets.std() * math.sqrt(252)
        assert fm.annualized_volatility(prices) == pytest.approx(expected)


class TestSharpeRatio:
    def test_flat_series_zero(self, flat_prices):
        # No volatility -> guard clause returns 0.
        assert fm.sharpe_ratio(flat_prices) == 0.0

    def test_positive_for_uneven_gainer(self):
        # Real (non-identical) positive-mean returns should give a positive Sharpe.
        # A perfectly steady +10%/day gives std=0 -> guarded to 0.0, which is
        # covered by test_flat_series_zero. Here we use uneven up-days.
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        prices = pd.Series([100.0, 105.0, 108.0, 115.0, 120.0], index=idx)
        assert fm.sharpe_ratio(prices) > 0


class TestSortinoRatio:
    def test_only_positive_returns_inf(self, rising_prices):
        # No downside days at all -> infinite Sortino by design.
        assert fm.sortino_ratio(rising_prices) == float("inf")

    def test_flat_series_zero(self, flat_prices):
        assert fm.sortino_ratio(flat_prices) == 0.0


# -----------------------------------------------------------------------------
# Drawdown / recovery
# -----------------------------------------------------------------------------

class TestMaxDrawdown:
    def test_known_50pct_dip(self, peak_trough_prices):
        # 100 -> 200 (peak) -> 100 is a -50% drawdown.
        assert fm.max_drawdown(peak_trough_prices) == pytest.approx(-0.50)

    def test_flat_series_zero(self, flat_prices):
        assert fm.max_drawdown(flat_prices) == pytest.approx(0.0)


class TestRecoveryDays:
    def test_recovered(self, peak_trough_prices):
        # Peak on day 2 (index 1), trough on day 3 (index 2), price 220 on day 5
        # is above the 200 peak -> recovered 2 days after trough.
        assert fm.recovery_days(peak_trough_prices) == 2

    def test_never_recovered(self, never_recovers_prices):
        assert fm.recovery_days(never_recovers_prices) is None


# -----------------------------------------------------------------------------
# Rolling metrics
# -----------------------------------------------------------------------------

class TestRollingVolatility:
    def test_first_values_nan(self, peak_trough_prices):
        # First (window-1) rolling values are NaN by definition.
        out = fm.rolling_volatility(peak_trough_prices, window=3)
        assert out.isna().sum() >= 2

    def test_last_value_finite(self, peak_trough_prices):
        out = fm.rolling_volatility(peak_trough_prices, window=2)
        assert not math.isnan(out.iloc[-1])


class TestRollingSharpe:
    def test_flat_window_is_nan(self):
        # Flat prices -> zero std -> guarded to NaN, not divide-by-zero.
        idx = pd.date_range("2024-01-01", periods=10, freq="D")
        s = pd.Series([100.0] * 10, index=idx)
        out = fm.rolling_sharpe(s, window=3)
        # All rolling values on a flat series should be NaN or 0.
        assert out.dropna().empty or (out.dropna() == 0).all()


# -----------------------------------------------------------------------------
# Portfolio / benchmark builders
# -----------------------------------------------------------------------------

class TestPortfolioSeries:
    def test_starts_at_one(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "AAA": [100.0, 110.0, 120.0],
            "BBB": [50.0, 55.0, 60.0],
        }, index=idx)
        out = fm.portfolio_series(df, {"AAA": 0.5, "BBB": 0.5})
        assert out.iloc[0] == pytest.approx(1.0)

    def test_weights_normalize(self):
        # Weights that don't sum to 1 should still work.
        idx = pd.date_range("2024-01-01", periods=2, freq="D")
        df = pd.DataFrame({"AAA": [100.0, 200.0]}, index=idx)
        out = fm.portfolio_series(df, {"AAA": 2.0})  # normalized -> 1.0
        assert out.iloc[-1] == pytest.approx(2.0)

    def test_ignores_unknown_ticker(self):
        idx = pd.date_range("2024-01-01", periods=2, freq="D")
        df = pd.DataFrame({"AAA": [100.0, 110.0]}, index=idx)
        out = fm.portfolio_series(df, {"AAA": 0.5, "MISSING": 0.5})
        # MISSING is dropped, so 100% weight ends up on AAA.
        assert out.iloc[-1] == pytest.approx(1.10)

    def test_zero_weights_empty(self):
        idx = pd.date_range("2024-01-01", periods=2, freq="D")
        df = pd.DataFrame({"AAA": [100.0, 110.0]}, index=idx)
        out = fm.portfolio_series(df, {"AAA": 0.0})
        assert out.empty


class TestBenchmarkGrowth:
    def test_starts_at_amount(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        prices = pd.Series([400.0, 420.0, 440.0], index=idx)
        out = fm.benchmark_growth(prices, idx, amount=10_000)
        assert out.iloc[0] == pytest.approx(10_000.0)
        assert out.iloc[-1] == pytest.approx(10_000 * 440 / 400)

    def test_empty_prices_returns_all_nan(self):
        # Empty upstream (e.g. SPY fetch failed) -> we return a series shaped
        # to the target index but full of NaN, so plotting code sees no line.
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        out = fm.benchmark_growth(pd.Series(dtype=float), idx, amount=1_000)
        assert out.isna().all()


class TestSavingsBenchmark:
    def test_starts_at_amount(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        out = fm.savings_benchmark(idx, amount=1_000, annual_rate=0.05)
        assert out.iloc[0] == pytest.approx(1_000.0)

    def test_grows_at_rate(self):
        # After exactly one year, value should equal amount * (1 + rate).
        idx = pd.date_range("2024-01-01", periods=366, freq="D")
        out = fm.savings_benchmark(idx, amount=1_000, annual_rate=0.05)
        # Day 365 is exactly one year later.
        assert out.iloc[-1] == pytest.approx(1_000 * 1.05, rel=1e-3)


class TestRealValueSeries:
    def test_no_inflation_is_identity(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        nominal = pd.Series([1_000.0, 1_100.0, 1_210.0], index=idx)
        out = fm.real_value_series(nominal, annual_inflation=0.0)
        pd.testing.assert_series_equal(out, nominal, check_names=False)

    def test_first_value_unchanged(self):
        idx = pd.date_range("2024-01-01", periods=10, freq="D")
        nominal = pd.Series(np.linspace(1_000, 2_000, 10), index=idx)
        out = fm.real_value_series(nominal, annual_inflation=0.05)
        assert out.iloc[0] == pytest.approx(nominal.iloc[0])


# -----------------------------------------------------------------------------
# Correlation matrix
# -----------------------------------------------------------------------------

class TestCorrelationMatrix:
    def test_perfect_positive_correlation(self):
        # Two series that move identically -> corr of 1.0.
        idx = pd.date_range("2024-01-01", periods=10, freq="D")
        series_a = pd.Series(np.linspace(100, 200, 10), index=idx)
        df = pd.DataFrame({"AAA": series_a, "BBB": series_a * 2})
        corr = fm.correlation_matrix(df)
        assert corr.loc["AAA", "BBB"] == pytest.approx(1.0)

    def test_empty_for_single_ticker(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({"AAA": [100.0, 110.0, 120.0, 130.0, 140.0]}, index=idx)
        out = fm.correlation_matrix(df)
        assert out.empty

    def test_empty_for_no_data(self):
        assert fm.correlation_matrix(pd.DataFrame()).empty


# -----------------------------------------------------------------------------
# Per-ticker returns + summary bundle
# -----------------------------------------------------------------------------

class TestPerTickerReturns:
    def test_basic(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "UP": [100.0, 110.0, 120.0],
            "DOWN": [100.0, 90.0, 80.0],
        }, index=idx)
        out = fm.per_ticker_returns(df)
        assert out["UP"] == pytest.approx(0.20)
        assert out["DOWN"] == pytest.approx(-0.20)


class TestSummaryMetrics:
    def test_keys_present(self, peak_trough_prices):
        out = fm.summary_metrics(peak_trough_prices)
        for key in ("total_return", "annual_return", "annual_volatility",
                    "sharpe", "sortino", "max_drawdown", "recovery_days"):
            assert key in out
