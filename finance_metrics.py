"""
finance_metrics.py
------------------
The math brain of the dashboard. Every function here takes clean pandas
data and returns a number or a Series. Keeping the math in its own file
(separate from the UI in app.py) is a good habit: it's easier to read,
easier to test, and easier for someone reviewing your code to follow.

Each function has a short note on WHAT the metric means, not just how it's
computed — that's the part worth actually learning.

Convention: there are ~252 trading days in a year. We use that to
"annualize" daily numbers so they're comparable to figures you'd see quoted
in the real world (e.g. "15% annual volatility").
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(prices: pd.Series) -> pd.Series:
    """
    Percent change from one day to the next.
    If a stock goes 100 -> 102, that day's return is 0.02 (2%).
    This is the foundation almost every other metric is built on.
    """
    return prices.pct_change().dropna()


def cumulative_returns(prices: pd.Series) -> pd.Series:
    """
    Growth of $1 invested at the start, over time.
    A value of 1.35 means $1 became $1.35 (a 35% total gain).
    Great for the 'how would my money have grown?' chart.
    """
    rets = daily_returns(prices)
    return (1 + rets).cumprod()


def total_return(prices: pd.Series) -> float:
    """The single headline number: total % gain/loss over the whole window."""
    if len(prices) < 2:
        return 0.0
    return prices.iloc[-1] / prices.iloc[0] - 1


def annualized_return(prices: pd.Series) -> float:
    """
    Total return re-expressed as a smooth yearly rate.
    Lets you compare a 3-month run against a 5-year run fairly.
    """
    rets = daily_returns(prices)
    if len(rets) == 0:
        return 0.0
    # Geometric mean daily return, then raised to a full year.
    growth = (1 + rets).prod()
    years = len(rets) / TRADING_DAYS
    if years == 0:
        return 0.0
    return growth ** (1 / years) - 1


def annualized_volatility(prices: pd.Series) -> float:
    """
    Volatility = how bumpy the ride is (the standard deviation of returns).
    Higher = more risk / bigger swings. We scale daily wobble up to a
    yearly figure by multiplying by sqrt(252).
    """
    rets = daily_returns(prices)
    if len(rets) == 0:
        return 0.0
    return rets.std() * np.sqrt(TRADING_DAYS)


def sharpe_ratio(prices: pd.Series, risk_free_rate: float = 0.04) -> float:
    """
    Return per unit of risk — the classic 'was it worth the stress?' number.
    Uses daily excess returns and annualizes the ratio, which is the standard
    textbook convention.
    """
    rets = daily_returns(prices)
    if len(rets) == 0:
        return 0.0

    rf_daily = (1 + risk_free_rate) ** (1 / TRADING_DAYS) - 1
    excess = rets - rf_daily
    std = excess.std()
    if std == 0:
        return 0.0
    return (excess.mean() / std) * np.sqrt(TRADING_DAYS)


def sortino_ratio(prices: pd.Series, risk_free_rate: float = 0.04) -> float:
    """
    Sharpe's downside-aware sibling: only penalizes harmful volatility.
    This is often easier to explain in portfolio reviews because upside
    volatility is not treated as 'bad'.
    """
    rets = daily_returns(prices)
    if len(rets) == 0:
        return 0.0

    rf_daily = (1 + risk_free_rate) ** (1 / TRADING_DAYS) - 1
    excess = rets - rf_daily
    downside = excess[excess < 0]

    if len(downside) == 0:
        return float("inf") if excess.mean() > 0 else 0.0

    downside_std = downside.std()
    if downside_std == 0:
        return float("inf") if excess.mean() > 0 else 0.0

    return (excess.mean() / downside_std) * np.sqrt(TRADING_DAYS)


def max_drawdown(prices: pd.Series) -> float:
    """
    The worst peak-to-trough drop, as a negative %.
    Answers: 'if I'd bought at the worst moment, how far down did I go
    before it recovered?' A gut-check on downside pain.
    """
    cum = cumulative_returns(prices)
    if len(cum) == 0:
        return 0.0
    running_peak = cum.cummax()          # highest point reached so far
    drawdown = cum / running_peak - 1    # how far below that peak we are
    return drawdown.min()                # the deepest dip


def recovery_days(prices: pd.Series) -> int | None:
    """
    Days it took to recover from the worst drawdown trough back to the prior
    peak level. Returns None if the series never recovered in the selected
    window.
    """
    cum = cumulative_returns(prices)
    if len(cum) == 0:
        return None

    running_peak = cum.cummax()
    drawdown = cum / running_peak - 1
    trough_level = drawdown.min()
    if trough_level >= 0:
        return 0

    trough_idx = drawdown.idxmin()
    peak_level = running_peak.loc[trough_idx]
    recovery_path = cum.loc[trough_idx:]
    recovered = recovery_path[recovery_path >= peak_level]
    if recovered.empty:
        return None

    recovered_idx = recovered.index[0]
    return int((recovered_idx - trough_idx).days)


def moving_average(prices: pd.Series, window: int) -> pd.Series:
    """
    Rolling average price over `window` days — smooths out noise so the
    underlying trend is visible. 50-day and 200-day are the famous ones;
    crossings between them are watched by a lot of traders.
    """
    return prices.rolling(window=window).mean()


def portfolio_series(price_df: pd.DataFrame, weights: dict) -> pd.Series:
    """
    Blend several stocks into one portfolio 'price' line using weights.
    weights is like {'AAPL': 0.5, 'MSFT': 0.5}. We normalize each stock to
    start at 1, scale by its weight, and sum — giving the growth of $1
    spread across the whole portfolio.
    """
    # Keep only tickers we actually have data for.
    cols = [c for c in weights if c in price_df.columns]
    if not cols:
        return pd.Series(dtype=float)

    # Normalize weights so they add up to 1 even if the user's don't.
    total_w = sum(weights[c] for c in cols)
    if total_w == 0:
        return pd.Series(dtype=float)

    # Fill gaps BEFORE normalizing. If the first row has a NaN for any ticker
    # (common when tickers' trading days don't line up perfectly), dividing by
    # it turns the whole series into NaN — that's the 'nan%' bug. ffill carries
    # the last known price forward; bfill covers any leading gap at the start.
    prices = price_df[cols].ffill().bfill()

    normalized = prices / prices.iloc[0]   # each ticker starts at 1
    weighted = sum(normalized[c] * (weights[c] / total_w) for c in cols)
    return weighted


def summary_metrics(prices: pd.Series, risk_free_rate: float = 0.04) -> dict:
    """Bundle the headline numbers together for easy display in the UI."""
    return {
        "total_return": total_return(prices),
        "annual_return": annualized_return(prices),
        "annual_volatility": annualized_volatility(prices),
        "sharpe": sharpe_ratio(prices, risk_free_rate),
        "sortino": sortino_ratio(prices, risk_free_rate),
        "max_drawdown": max_drawdown(prices),
        "recovery_days": recovery_days(prices),
    }


def per_ticker_returns(price_df: pd.DataFrame) -> dict:
    """
    Total % return over the window for each ticker individually.
    Used for the holdings breakdown (which names carried the portfolio).
    """
    out = {}
    clean = price_df.ffill().bfill()
    for col in clean.columns:
        s = clean[col].dropna()
        out[col] = (s.iloc[-1] / s.iloc[0] - 1) if len(s) >= 2 else 0.0
    return out


def savings_benchmark(index: pd.DatetimeIndex, amount: float,
                      annual_rate: float) -> pd.Series:
    """
    'What if the money just sat in a high-yield savings account?'
    Grows `amount` at a flat annual rate, compounded smoothly across the same
    dates as the portfolio, so we can overlay it as a fair benchmark line.
    This answers the everyday question: was the market risk even worth it?
    """
    days = (index - index[0]).days.to_numpy().astype(float)
    vals = amount * (1 + annual_rate) ** (days / 365.0)
    return pd.Series(vals, index=index)


def real_value_series(value_series: pd.Series, annual_inflation: float) -> pd.Series:
    """
    Convert nominal dollars into 'real' (today's-purchasing-power) dollars.
    $13k in the future isn't worth $13k now if prices rose meanwhile — we
    divide by an inflation 'deflator' that grows over time. This is the gap
    between the number on your statement and what it actually buys.
    """
    idx = value_series.index
    years = (idx - idx[0]).days.to_numpy().astype(float) / 365.0
    deflator = (1 + annual_inflation) ** years
    return pd.Series(value_series.to_numpy() / deflator, index=idx)


def benchmark_growth(prices: pd.Series, index: pd.DatetimeIndex,
                     amount: float) -> pd.Series:
    """
    'What if you'd put the same money into a market index like SPY instead?'
    Align a benchmark price series to the portfolio's date range, normalize it
    to start at 1, and scale to the same starting dollar amount. This is the
    fair 'did you actually beat the market?' comparison line.
    """
    if prices.empty or index.empty:
        return pd.Series(dtype=float, index=index)
    aligned = prices.reindex(index).ffill().bfill()
    if aligned.empty or aligned.iloc[0] == 0 or pd.isna(aligned.iloc[0]):
        return pd.Series(dtype=float, index=index)
    return (aligned / aligned.iloc[0]) * amount


def rolling_volatility(prices: pd.Series, window: int = 30) -> pd.Series:
    """
    Annualized volatility computed over a rolling window — a "how bumpy is the
    ride *right now*?" line, instead of a single number for the whole period.
    A rising line = the market is getting choppier; falling = calming down.
    """
    rets = daily_returns(prices)
    if rets.empty:
        return pd.Series(dtype=float)
    return rets.rolling(window).std() * np.sqrt(TRADING_DAYS)


def rolling_sharpe(prices: pd.Series, window: int = 30,
                   risk_free_rate: float = 0.04) -> pd.Series:
    """
    Rolling Sharpe ratio: return-per-unit-of-risk over a moving window.
    Positive and rising = the portfolio is being *paid* for the risk it's
    taking. Negative = you're taking risk without reward.
    """
    rets = daily_returns(prices)
    if rets.empty:
        return pd.Series(dtype=float)
    rf_daily = (1 + risk_free_rate) ** (1 / TRADING_DAYS) - 1
    excess = rets - rf_daily
    mean = excess.rolling(window).mean()
    std = excess.rolling(window).std()
    # Guard against divide-by-zero on flat windows.
    ratio = (mean / std.replace(0, np.nan)) * np.sqrt(TRADING_DAYS)
    return ratio


def correlation_matrix(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    How closely each pair of holdings moves together, on a scale of −1 to +1.
    +1 = they always rise/fall together (concentrated risk — bad for
    diversification). 0 = independent. −1 = they hedge each other.
    Computed on daily returns, not prices, so trend size doesn't dominate.
    """
    if price_df.empty or len(price_df.columns) < 2:
        return pd.DataFrame()
    rets = price_df.ffill().bfill().pct_change().dropna(how="all")
    if rets.empty:
        return pd.DataFrame()
    return rets.corr()