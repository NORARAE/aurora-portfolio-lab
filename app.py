"""
app.py — Aurora Portfolio Lab
-----------------------------
A premium fintech-style portfolio dashboard: live stocks AND crypto, real
risk metrics, a high-yield-savings benchmark, inflation-adjusted "real"
returns, and an AI read on the news.

Design: dark 'aurora' palette (from the Node Bloom piece) with the layout of
a modern trading app (Webull / crypto.com) — a big hero value, time pills, a
clean gradient chart, and a responsive card grid that stacks on phones.

Run:  streamlit run app.py
Math lives in finance_metrics.py, AI in sentiment.py. This file is UI + flow.
"""

import datetime as dt
import html
import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

import finance_metrics as fm
import sentiment as sent

st.set_page_config(page_title="Aurora · Portfolio Lab", page_icon="✦", layout="wide")

# --- Palette ---
BG       = "#0b0a12"; SURFACE = "#15131f"; SURFACE2 = "#1c1a28"
BORDER   = "rgba(255,255,255,0.07)"; TEXT = "#edeef4"; MUTED = "#8b8ca6"
UP       = "#16c784"; DOWN = "#ea3943"
ACCENT   = "#8b7bf7"; ACCENT2 = "#4de1d0"; GOLD = "#f5c451"

# Slice/segment palette for allocation visuals (donut + holdings bars).
# Reuses existing tokens only — introduces no new colors.
ALLOC_COLORS = [ACCENT, ACCENT2, GOLD, UP]

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  .stApp {{
    background:
      radial-gradient(90% 60% at 12% -5%, rgba(139,123,247,0.10), transparent 60%),
      radial-gradient(90% 60% at 95% 0%, rgba(77,225,208,0.06), transparent 55%),
      {BG};
    color: {TEXT};
  }}
  html {{ font-size: 14px; }}
  html, body, [class*="css"], .stMarkdown, p, span, div {{
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    font-feature-settings: 'tnum';
  }}
  body {{ line-height: 1.45; }}
  #MainMenu, footer, header {{ visibility: hidden; }}
  .block-container {{ padding-top: 1.05rem; padding-bottom: 1.75rem; max-width: 1120px; }}

  .brand {{ font-size: 1.3rem; font-weight: 800; letter-spacing: -0.01em; }}
  .brand .mark {{ background: linear-gradient(90deg, {ACCENT2}, {ACCENT});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .sig {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; opacity: 0.9; }}
  .sig a {{ color: {GOLD}; text-decoration: none; border-bottom: 1px solid rgba(245,196,81,0.45); }}

  /* Hero */
  .hero {{ background: linear-gradient(160deg, {SURFACE2}, {SURFACE});
    border: 1px solid {BORDER}; border-radius: 20px;
    padding: 1.15rem 1.3rem 0.5rem 1.3rem; margin-bottom: 0.62rem;
    box-shadow: 0 20px 50px rgba(0,0,0,0.35); }}
  .hero-label {{ color: {MUTED}; font-size: 0.66rem; font-weight: 600;
    letter-spacing: 0.12em; text-transform: uppercase; }}
  .hero-value {{ font-size: 2.55rem; font-weight: 800; letter-spacing: -0.03em;
    line-height: 1.05; margin-top: 0.1rem; }}
  .chip {{ display: inline-flex; align-items: center; gap: 0.35rem; font-weight: 700;
    font-size: 0.92rem; padding: 0.2rem 0.58rem; border-radius: 10px; }}
  .chip.up {{ color: {UP}; background: rgba(22,199,132,0.12); }}
  .chip.down {{ color: {DOWN}; background: rgba(234,57,67,0.12); }}

  /* Verdict strip */
  .verdict {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 0.58rem; margin-bottom: 0.62rem; }}
  .vcard {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
    padding: 0.78rem 0.9rem; position: relative; overflow: hidden; }}
  .vcard::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, {ACCENT2}, {ACCENT}); opacity:0.8; }}
  .vcard .vlabel {{ color: {MUTED}; font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; }}
  .vcard .vmain {{ font-size: 1.18rem; font-weight: 800; margin-top: 0.22rem; letter-spacing: -0.02em; }}
  .vcard .vsub {{ color: {MUTED}; font-size: 0.72rem; margin-top: 0.12rem; }}

  /* Stat grid: fixed 4-up on wide screens, 2-up on smaller screens */
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.56rem; margin-bottom: 0.25rem; }}
  .stat {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
    padding: 0.76rem 0.88rem; transition: transform 0.15s ease, border-color 0.15s ease; }}
  .stat:hover {{ transform: translateY(-2px); border-color: rgba(139,123,247,0.35); }}
  .stat-label {{ color: {MUTED}; font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; }}
  .stat-value {{ font-size: 1.28rem; font-weight: 800; letter-spacing: -0.02em; margin-top: 0.2rem; }}
  .stat-sub {{ color: {MUTED}; font-size: 0.66rem; margin-top: 0.14rem; line-height: 1.34; }}
  .up-t {{ color: {UP}; }} .down-t {{ color: {DOWN}; }} .gold-t {{ color: {GOLD}; }} .neutral-t {{ color: {TEXT}; }}

  /* Holdings */
  .holding {{ display: flex; justify-content: space-between; align-items: center;
    padding: 0.62rem 0.78rem; margin-bottom: 0.38rem; background: {SURFACE};
    border: 1px solid {BORDER}; border-radius: 12px; }}
  .tkr {{ font-weight: 700; font-size: 0.93rem; }}
  .tkr-sub {{ color: {MUTED}; font-size: 0.68rem; }}

  .section {{ color: {MUTED}; font-size: 0.66rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; margin: 0.72rem 0 0.42rem 0; }}
  .badge {{ display:inline-block; padding: 0.3rem 0.8rem; border-radius: 999px; font-weight: 700;
    font-size: 0.7rem; padding: 0.21rem 0.58rem; border: 1px solid rgba(245,196,81,0.3); background: rgba(245,196,81,0.08); color: {GOLD}; }}
  .news {{ border-left: 2px solid rgba(139,123,247,0.4); padding: 0.5rem 0.85rem; margin: 0.4rem 0;
    color: {TEXT}; font-size: 0.79rem; padding: 0.42rem 0.66rem; margin: 0.28rem 0; background: {SURFACE}; border-radius: 0 10px 10px 0; }}
  [data-testid="stCaptionContainer"] p {{
    color: {MUTED};
    font-size: 0.68rem;
    letter-spacing: 0.014em;
    line-height: 1.36;
  }}
  [data-testid="stPopoverButton"] {{
    font-size: 0.66rem;
    letter-spacing: 0.01em;
  }}
  [data-testid="stPopover"] [data-testid="stMarkdownContainer"] p,
  [data-testid="stPopover"] [data-testid="stMarkdownContainer"] li {{
    font-size: 0.7rem;
    line-height: 1.25;
    margin: 0.08rem 0;
  }}
  [data-testid="stPopover"] [data-testid="stMarkdownContainer"] ul,
  [data-testid="stPopover"] [data-testid="stMarkdownContainer"] ol {{
    margin: 0.2rem 0 0.35rem 0;
    padding-left: 1rem;
  }}
  [data-testid="stPopover"] [data-testid="stMarkdownContainer"] strong {{
    letter-spacing: 0.01em;
  }}
  [data-testid="stPopover"] .stVerticalBlock {{
    max-height: 52vh;
    overflow-y: auto;
    padding-right: 4px;
  }}

  section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
  [data-testid="stSidebar"] .stButton button {{ background: {SURFACE2}; border: 1px solid {BORDER};
    color: {TEXT}; border-radius: 10px; font-size: 0.72rem; font-weight: 600; padding: 0.18rem 0; }}
  [data-testid="stSidebar"] .stButton button:hover {{ border-color: {ACCENT}; color: {ACCENT2}; }}

  [data-testid="stExpander"] details {{
    background: {SURFACE2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 0.58rem;
  }}
  [data-testid="stExpander"] details > summary {{
    min-height: 44px;
    padding: 0.5rem 0.7rem;
    color: {TEXT};
    font-weight: 700;
    letter-spacing: 0.01em;
  }}
  [data-testid="stExpander"] details > summary p {{
    margin: 0;
    font-size: 0.82rem;
    color: {TEXT};
  }}
  .controls-star {{
    font-weight: 800;
    background: linear-gradient(90deg, {ACCENT}, {ACCENT2});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
  }}

  /* Phone tuning */
  @media (max-width: 640px) {{
    html {{ font-size: 13px; }}
    .hero-value {{ font-size: 1.92rem; }}
    .hero {{ padding: 0.95rem 0.92rem 0.44rem 0.92rem; }}
    .block-container {{ padding-left: 0.8rem; padding-right: 0.8rem; }}
    .stat-value {{ font-size: 1.16rem; }}

    [data-testid="stExpander"] details > summary {{
      min-height: 44px;
    }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] details > summary {{
      transition: none !important;
      animation: none !important;
    }}
  }}

  @media (max-width: 980px) {{
    .stat-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  }}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def load_prices(tickers: tuple[str, ...], years: int = 5) -> pd.DataFrame:
    """Fetch daily Close per ticker (stocks OR crypto like BTC-USD),
    one clean column each. Per-ticker .history() avoids yfinance's shifting
    multi-ticker column shapes — the source of the earlier empty-chart bug."""
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * years + 10)
    frames = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(start=start, end=end, auto_adjust=True)
            if not hist.empty and "Close" in hist:
                s = hist["Close"].copy()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                frames[t] = s
        except Exception:
            pass
    return pd.DataFrame(frames).dropna(how="all") if frames else pd.DataFrame()


def slice_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = {"1M": 30, "3M": 91, "6M": 182, "1Y": 365, "2Y": 730}.get(period)
    if days is None:
        return df
    cutoff = pd.Timestamp(dt.date.today() - dt.timedelta(days=days))
    return df.loc[df.index >= cutoff]


def label(t: str) -> str:
    """Display name: BTC-USD -> BTC, but leave stock tickers alone."""
    return t.replace("-USD", "") if t.endswith("-USD") else t

def money(x: float) -> str:  return f"${x:,.0f}"
def pct(x: float) -> str:    return f"{x*100:+.2f}%"


def esc(s) -> str:
    """HTML-escape untrusted text before it enters unsafe_allow_html markup.
    News headlines (external), Claude summaries (LLM output), and ticker labels
    (user input) are all untrusted — escaping prevents HTML/script injection."""
    return html.escape(str(s), quote=True)


def build_export_csv(value_series, savings_series, real_series, per, weights, total_w) -> str:
    """Assemble a two-section CSV: the portfolio value time-series plus a
    per-holding return table for the selected window. Presentation-only — it
    just formats already-computed series, it does no finance math."""
    buf = io.StringIO()
    buf.write("# Aurora Portfolio Lab — data export\n")
    buf.write("# Section 1: portfolio value series\n")
    pd.DataFrame({
        "date": value_series.index.strftime("%Y-%m-%d"),
        "portfolio_value": value_series.round(2).to_numpy(),
        "savings_benchmark": savings_series.round(2).to_numpy(),
        "real_value": real_series.round(2).to_numpy(),
    }).to_csv(buf, index=False)
    buf.write("\n# Section 2: per-holding return (this window)\n")
    pd.DataFrame([
        {"ticker": label(t),
         "weight_pct": round(weights.get(t, 0) / total_w * 100, 2),
         "total_return_pct": round(r * 100, 2)}
        for t, r in sorted(per.items(), key=lambda kv: -(weights.get(kv[0], 0.0)))
    ]).to_csv(buf, index=False)
    return buf.getvalue()


def add_ticker(sym: str):
    """Callback for quick-add chips (runs before widgets re-instantiate)."""
    cur = [t.strip().upper() for t in st.session_state.get("tickers_text", "").split(",") if t.strip()]
    if sym not in cur:
        cur.append(sym)
        st.session_state.tickers_text = ", ".join(cur)


def equalize_alloc(tickers: list[str], mode: str):
    """Reset every holding to an equal split. Runs as a button callback (before
    the widgets rebuild), so it can safely write the per-ticker widget state."""
    n = max(len(tickers), 1)
    if mode == "$ amount":
        # Spread the current total (or a sensible default) evenly across holdings.
        total = sum(float(st.session_state.get(f"amt_{t}", 0)) for t in tickers) or 10_000.0
        for t in tickers:
            st.session_state[f"amt_{t}"] = round(total / n)
    else:
        split = _allocate_int_total({t: 1.0 for t in tickers}, 100)
        for t in tickers:
            st.session_state[f"pct_{t}"] = split.get(t, 0)


def _allocate_int_total(raw: dict[str, float], total: int) -> dict[str, int]:
    """Convert arbitrary non-negative weights into integer shares summing to `total`.
    Uses largest-remainder rounding so percent sliders can always sum to 100 exactly."""
    keys = list(raw.keys())
    if not keys:
        return {}
    clean = {k: max(0.0, float(v)) for k, v in raw.items()}
    denom = sum(clean.values())
    if denom <= 0:
        clean = {k: 1.0 for k in keys}
        denom = float(len(keys))

    scaled = {k: (clean[k] / denom) * total for k in keys}
    base = {k: int(scaled[k]) for k in keys}
    remainder = total - sum(base.values())
    order = sorted(keys, key=lambda k: (scaled[k] - base[k]), reverse=True)
    for k in order[:remainder]:
        base[k] += 1
    return base


def rebalance_pct(changed_ticker: str, tickers: tuple[str, ...]):
    """Keep percent sliders at an exact 100% total after any single slider move."""
    symbols = [t for t in tickers if t]
    if not symbols or changed_ticker not in symbols:
        return

    changed_key = f"pct_{changed_ticker}"
    changed_val = int(st.session_state.get(changed_key, 0))
    changed_val = max(0, min(100, changed_val))
    st.session_state[changed_key] = changed_val

    others = [t for t in symbols if t != changed_ticker]
    if not others:
        st.session_state[changed_key] = 100
        return

    remaining = 100 - changed_val
    if remaining <= 0:
        for t in others:
            st.session_state[f"pct_{t}"] = 0
        return

    prev = {t: float(st.session_state.get(f"pct_{t}", 0)) for t in others}
    if sum(max(0.0, v) for v in prev.values()) <= 0:
        prev = {t: 1.0 for t in others}

    alloc = _allocate_int_total(prev, remaining)
    for t, v in alloc.items():
      st.session_state[f"pct_{t}"] = v


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
if "tickers_text" not in st.session_state:
    st.session_state.tickers_text = "AAPL, MSFT, NVDA"
st.session_state.setdefault("invested", 10_000)   # master portfolio amount ($)

with st.sidebar:
    st.markdown('<div class="section" style="margin-top:0">Assets</div>', unsafe_allow_html=True)
    tickers_raw = st.text_input("Tickers (stocks or crypto)", key="tickers_text")
    # De-dupe (preserve order) and cap the count: each ticker is a live network
    # call, so an accidental huge paste shouldn't fan out into hundreds of fetches.
    MAX_TICKERS = 15
    _seen: set[str] = set()
    tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
    tickers = [t for t in tickers if not (t in _seen or _seen.add(t))]
    if len(tickers) > MAX_TICKERS:
        st.caption(f"Using the first {MAX_TICKERS} of {len(tickers)} tickers.")
        tickers = tickers[:MAX_TICKERS]

    st.caption("Quick add")
    quick = [("BTC-USD", "＋ BTC"), ("ETH-USD", "＋ ETH"), ("SPY", "＋ SPY"),
             ("TSLA", "＋ TSLA"), ("AMZN", "＋ AMZN"), ("GOOGL", "＋ GOOGL")]
    qcols = st.columns(3)
    for i, (sym, lbl) in enumerate(quick):
        qcols[i % 3].button(lbl, key=f"add_{sym}", on_click=add_ticker,
                            args=(sym,), width="stretch")

    # --- Investment & allocation ------------------------------------------
    # Two lenses on the same split: percent weights OR dollar amounts. Either
    # way portfolio_series() normalizes it, so the math downstream is identical
    # — this block only needs to produce `weights` (dict) and `amount` (float).
    st.markdown('<div class="section">Investment & allocation</div>', unsafe_allow_html=True)
    st.number_input(
      "Hypothetical investment ($)",
      min_value=500,
      max_value=1_000_000,
      step=500,
      key="invested",
      format="%d",
      help="This is the single investment input used across the dashboard.",
    )
    alloc_mode = st.segmented_control(
        "Allocation mode", ["% weight", "$ amount"],
        default="% weight", key="alloc_mode", label_visibility="collapsed") or "% weight"

    n_hold = max(len(tickers), 1)
    st.button("⚖ Equalize", on_click=equalize_alloc, args=(tickers, alloc_mode),
              width="stretch", help="Split evenly across every holding.")

    if alloc_mode == "$ amount":
        st.caption("Dollars set the ratio between holdings — scaled to fit your investment.")
        for t in tickers:                       # seed defaults, then build widgets without value=
            st.session_state.setdefault(f"amt_{t}", round(10_000 / n_hold))
        dollars = {t: float(st.number_input(label(t), min_value=0, step=100,
                                            key=f"amt_{t}", format="%d")) for t in tickers}
        weights = dict(dollars)                 # relative amounts; normalized in portfolio_series
    else:
        st.caption("Percent in each holding (auto-balances to 100%).")
        initial_split = _allocate_int_total({t: 1.0 for t in tickers}, 100)
        for t in tickers:
            st.session_state.setdefault(f"pct_{t}", initial_split.get(t, 0))
        pcts = {
            t: st.slider(
                label(t),
                0,
                100,
                key=f"pct_{t}",
                format="%d%%",
                on_change=rebalance_pct,
                args=(t, tuple(tickers)),
            )
            for t in tickers
        }
        weights = {t: v / 100.0 for t, v in pcts.items()}

    # The investment amount is the single source of truth, set on the main page
    # (modal + slider). Allocation here just splits it; the $ shown are derived.
    amount = float(st.session_state.get("invested", 10_000))

    # Live recap: a stacked allocation bar + the resulting % and $ per holding.
    total_w = sum(weights.values())
    if total_w > 0:
        seg = [ACCENT2, ACCENT, GOLD, UP, "#e879f9", "#60a5fa"]
        ordered = sorted(weights.items(), key=lambda kv: -kv[1])
        bar = ('<div style="display:flex;height:8px;border-radius:6px;'
               'overflow:hidden;margin:0.15rem 0 0.55rem 0;">')
        recap = ""
        for i, (t, w) in enumerate(ordered):
            share = w / total_w
            color = seg[i % len(seg)]
            bar += f'<div style="width:{share*100:.4f}%;background:{color};"></div>'
            recap += (f'<div style="display:flex;justify-content:space-between;'
                      f'font-size:0.76rem;padding:0.1rem 0;">'
                      f'<span style="color:{TEXT};"><span style="display:inline-block;width:8px;'
                      f'height:8px;border-radius:2px;background:{color};margin-right:6px;"></span>'
                      f'{esc(label(t))}</span><span style="color:{MUTED};">'
                      f'{share*100:.0f}% · {money(amount*share)}</span></div>')
        st.markdown(bar + '</div>' + recap, unsafe_allow_html=True)

        if alloc_mode == "% weight":
            entered = sum(int(st.session_state.get(f"pct_{t}", 0)) for t in tickers)
            st.caption(f"Splitting {money(amount)} · sliders total {entered}% (locked to 100%).")
        else:
            st.caption(f"Splitting {money(amount)} by the ratios above.")
    else:
        st.caption("Give a holding a non-zero share to build the portfolio.")

    st.markdown('<div class="section">Benchmarks & assumptions</div>', unsafe_allow_html=True)
    savings_apy = st.slider("High-yield savings APY", 0.0, 0.08, 0.04, 0.005,
                            help="The 'safe' alternative your portfolio is compared against.")
    inflation = st.slider("Annual inflation", 0.0, 0.10, 0.038, 0.002,
                          help="Used to show real, inflation-adjusted returns. ~3.8% recently.")
    rf = st.slider("Risk-free rate (Sharpe)", 0.0, 0.08, 0.04, 0.005)

    st.markdown('<div class="section">Display</div>', unsafe_allow_html=True)
    show_real = st.toggle("Show inflation-adjusted line", value=False)
    run_sentiment = st.toggle("AI news sentiment", value=True)
    use_source_weighting = st.toggle(
      "Source credibility weighting",
      value=True,
      help="Applies light source-trust weights to headline sentiment before averaging.",
      disabled=not run_sentiment,
    )


# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
with st.expander("✦ Controls & filters  ▾", expanded=False):
  st.caption("Open the ‹ arrow at top-left to adjust tickers, weights, and assumptions")

h1, h2 = st.columns([3, 2])
with h1:
    st.markdown('<div class="brand"><span class="mark">✦ Aurora</span> Portfolio Lab</div>',
                unsafe_allow_html=True)
with h2:
    st.markdown(
        '<div style="text-align:right" class="sig">designed + coded by '
        '<a href="https://www.linkedin.com/in/ngenetti/" target="_blank">PlayPlayCode ↗</a></div>',
        unsafe_allow_html=True)

if not tickers:
    st.info("Add at least one asset in the sidebar — stocks like AAPL or crypto like BTC-USD.")
    st.stop()

with st.spinner("Loading market data…"):
    full = load_prices(tuple(tickers))

if full.empty:
    st.error("No data came back. Check the symbols (crypto needs the -USD suffix, e.g. BTC-USD).")
    st.stop()

missing = [t for t in tickers if t not in full.columns]
if missing:
    st.warning(f"No data for: {', '.join(missing)} — skipping. (Crypto needs -USD, e.g. ETH-USD.)")

# ----------------------------------------------------------------------------
# RANGE + CORE SERIES
# ----------------------------------------------------------------------------
period = st.pills("Range", ["1M", "3M", "6M", "1Y", "2Y", "MAX"],
                  default="1Y", label_visibility="collapsed") or "1Y"

view = slice_period(full, period)
port_growth = fm.portfolio_series(view, weights)
if port_growth.empty:
    st.info("Give at least one holding a non-zero allocation in the sidebar.")
    st.stop()
value_series = port_growth * amount
savings_series = fm.savings_benchmark(value_series.index, amount, savings_apy)
real_series = fm.real_value_series(value_series, inflation)

current_value = float(value_series.iloc[-1])
change_dollars = current_value - amount
change_pct = float(port_growth.iloc[-1] - 1)
gained = change_dollars >= 0

years_elapsed = max((value_series.index[-1] - value_series.index[0]).days / 365.0, 1e-9)
real_final = float(real_series.iloc[-1])
real_return = real_final / amount - 1
savings_final = float(savings_series.iloc[-1])
vs_savings = current_value - savings_final

# ----------------------------------------------------------------------------
# HERO
# ----------------------------------------------------------------------------
chip_cls = "up" if gained else "down"
arrow = "▲" if gained else "▼"
st.markdown(f"""
<div class="hero">
  <div class="hero-label">Portfolio value · {money(amount)} invested {period} ago</div>
  <div style="display:flex; align-items:baseline; gap:0.8rem; flex-wrap:wrap;">
    <span class="hero-value">{money(current_value)}</span>
    <span class="chip {chip_cls}">{arrow} {money(abs(change_dollars))} ({pct(change_pct)})</span>
  </div>
</div>
""", unsafe_allow_html=True)

fig = go.Figure()
# Vertical "aurora glow" under the line: solid near the price, fading to nothing
# at the axis. Plotly 6's fillgradient (new to us) replaces the old flat fillcolor.
grad_rgb = "22,199,132" if gained else "234,57,67"
fig.add_trace(go.Scatter(x=value_series.index, y=value_series, mode="lines", name="Portfolio",
    line=dict(color=UP if gained else DOWN, width=2.4, shape="spline"), fill="tozeroy",
    fillgradient=dict(type="vertical", colorscale=[
        (0.0, f"rgba({grad_rgb},0.00)"), (1.0, f"rgba({grad_rgb},0.34)")]),
    hovertemplate="%{x|%b %d, %Y}<br><b>$%{y:,.0f}</b><extra>Portfolio</extra>"))
fig.add_trace(go.Scatter(x=savings_series.index, y=savings_series, mode="lines",
    name=f"Savings @ {savings_apy*100:.1f}%",
    line=dict(color=GOLD, width=1.4, dash="dash"),
    hovertemplate="%{x|%b %d, %Y}<br>$%{y:,.0f}<extra>Savings</extra>"))
series_range = [value_series, savings_series]
if show_real:
    fig.add_trace(go.Scatter(x=real_series.index, y=real_series, mode="lines",
        name="Real (infl-adj)", line=dict(color=ACCENT, width=1.6),
        hovertemplate="%{x|%b %d, %Y}<br>$%{y:,.0f}<extra>Real</extra>"))
    series_range.append(real_series)

lo = min(float(s.min()) for s in series_range)
hi = max(float(s.max()) for s in series_range)
pad = (hi - lo) * 0.12 or hi * 0.02
fig.update_layout(height=292, margin=dict(l=0, r=0, t=6, b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=MUTED, family="Inter"),
    legend=dict(orientation="h", y=1.14, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    xaxis=dict(showgrid=False, ticks="", color=MUTED, showspikes=True,
               spikemode="across", spikethickness=1, spikedash="dot",
               spikecolor="rgba(255,255,255,0.22)", spikesnap="cursor"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False,
               ticks="", tickprefix="$", side="right", color=MUTED, range=[lo - pad, hi + pad]),
    hovermode="x unified", hoverlabel=dict(bgcolor=SURFACE2, font_color=TEXT, bordercolor=BORDER))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ----------------------------------------------------------------------------
# VERDICT STRIP (the everyday "was it worth it?" answer)
# ----------------------------------------------------------------------------
beat = vs_savings >= 0
st.markdown(f"""
<div class="verdict">
  <div class="vcard">
    <div class="vlabel">vs. high-yield savings</div>
    <div class="vmain {'up-t' if beat else 'down-t'}">{'+'if beat else '−'}{money(abs(vs_savings))}</div>
    <div class="vsub">{'Ahead of' if beat else 'Behind'} a {savings_apy*100:.1f}% savings account</div>
  </div>
  <div class="vcard">
    <div class="vlabel">Real return · after {inflation*100:.1f}% inflation</div>
    <div class="vmain {'up-t' if real_return>=0 else 'down-t'}">{pct(real_return)}</div>
    <div class="vsub">Nominal was {pct(change_pct)} — inflation ate the gap</div>
  </div>
  <div class="vcard">
    <div class="vlabel">Real value today</div>
    <div class="vmain neutral-t">{money(real_final)}</div>
    <div class="vsub">What {money(current_value)} actually buys in today's dollars</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# STAT CARDS (responsive grid)
# ----------------------------------------------------------------------------
sh1, sh2 = st.columns([5, 1])
with sh1:
  st.markdown('<div class="section" style="margin-top:0.4rem">Risk & quality snapshot</div>', unsafe_allow_html=True)
with sh2:
  with st.popover("Metric guide"):
    st.markdown("""
**How to read these**

- **Total return / CAGR**: headline growth.
- **Sortino**: return adjusted for downside risk only.
- **Max drawdown**: worst peak-to-trough drop.
- **Recovery**: days to reclaim the prior peak.
""")

m = fm.summary_metrics(port_growth, risk_free_rate=rf)
def cell(lbl, val, cls, tip="", sub=""):
    hint = f' title="{esc(tip)}"' if tip else ""
    sub_html = f'<div class="stat-sub">{sub}</div>' if sub else ""
    return f'<div class="stat"><div class="stat-label"{hint}>{lbl}</div><div class="stat-value {cls}">{val}</div>{sub_html}</div>'

short_window = period in {"1M", "3M", "6M"}
ret_label = "Total return" if short_window else "CAGR"
total_ret = float(m.get("total_return", fm.total_return(port_growth)))
annual_ret = float(m.get("annual_return", fm.annualized_return(port_growth)))
max_dd = float(m.get("max_drawdown", fm.max_drawdown(port_growth)))
sharpe = float(m.get("sharpe", fm.sharpe_ratio(port_growth, rf)))
ret_value = total_ret if short_window else annual_ret

sortino = m.get("sortino")
if sortino is None:
    sortino_fn = getattr(fm, "sortino_ratio", None)
    sortino = float(sortino_fn(port_growth, rf)) if callable(sortino_fn) else sharpe

if sortino == float("inf"):
    sortino_text = "∞"
    sortino_cls = "up-t"
else:
    sortino_text = f"{float(sortino):.2f}"
    sortino_cls = "up-t" if sortino >= 1 else ("down-t" if sortino < 0 else "gold-t")

recovery = m.get("recovery_days")
if recovery is None:
    recovery_fn = getattr(fm, "recovery_days", None)
    recovery = recovery_fn(port_growth) if callable(recovery_fn) else None

if recovery is None:
    recovery_text = "Not yet"
    recovery_cls = "down-t"
else:
    recovery_text = f"{int(recovery)}d"
    recovery_cls = "up-t" if recovery <= 60 else "gold-t"

st.markdown('<div class="stat-grid">'
    + cell(ret_label, pct(ret_value), "up-t" if ret_value >= 0 else "down-t",
      sub="Headline growth in this window")
    + cell("Sortino ratio", sortino_text, sortino_cls,
      tip=f"Sharpe (daily excess, annualized): {sharpe:.2f}",
      sub="Return per unit of downside risk")
    + cell("Max drawdown", f'{max_dd*100:.1f}%', "down-t",
      sub="Largest peak-to-trough decline")
    + cell("Recovery", recovery_text, recovery_cls,
      tip="Days from worst trough back to prior peak",
      sub="Time needed to regain prior high")
    + '</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# HOLDINGS + ALLOCATION DONUT (ranked allocation table beside a weights donut)
# ----------------------------------------------------------------------------
st.markdown('<div class="section">Holdings · this window</div>', unsafe_allow_html=True)
per = fm.per_ticker_returns(view)
hold_total_w = sum(weights[t] for t in per if t in weights) or 1
# Rank by allocation weight so the rows + bars read like a ranked table; assign
# each holding a stable slice color the donut reuses as a consistent visual key.
ranked = sorted(per.items(), key=lambda kv: -(weights.get(kv[0], 0.0)))
color_for = {t: ALLOC_COLORS[i % len(ALLOC_COLORS)] for i, (t, _) in enumerate(ranked)}

st.markdown(f"""
<style>
  .holding {{ gap: 0.7rem; }}
  .h-name {{ min-width: 54px; font-weight: 700; font-size: 0.9rem; color: {TEXT}; }}
  .h-bar {{ flex: 1; height: 6px; background: rgba(255,255,255,0.06);
    border-radius: 4px; overflow: hidden; }}
  .h-bar-fill {{ height: 100%; border-radius: 4px; }}
  .h-share {{ color: {TEXT}; font-size: 0.78rem; font-weight: 700;
    min-width: 40px; text-align: right; }}
  .h-ret {{ font-weight: 800; font-size: 0.98rem; min-width: 76px; text-align: right; }}
</style>
""", unsafe_allow_html=True)

hcol1, hcol2 = st.columns([1.7, 1], gap="medium")
with hcol1:
    rows = ""
    for t, r in ranked:
        w = weights.get(t, 0) / hold_total_w
        cls = "up-t" if r >= 0 else "down-t"
        rows += (
            f'<div class="holding">'
            f'<div class="h-name">{esc(label(t))}</div>'
            f'<div class="h-bar"><div class="h-bar-fill" '
            f'style="width:{w*100:.2f}%;background:{color_for[t]};"></div></div>'
            f'<div class="h-share">{w*100:.0f}%</div>'
            f'<div class="h-ret {cls}">{pct(r)}</div>'
            f'</div>'
        )
    st.markdown(rows, unsafe_allow_html=True)
with hcol2:
    donut = go.Figure(go.Pie(
        labels=[label(t) for t, _ in ranked],
        values=[weights.get(t, 0) / hold_total_w for t, _ in ranked],
        hole=0.62, sort=False, direction="clockwise",
        marker=dict(colors=[color_for[t] for t, _ in ranked], line=dict(color=BG, width=2)),
        textposition="inside", textinfo="label", insidetextorientation="horizontal",
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
    ))
    donut.update_layout(
        height=200, margin=dict(l=4, r=4, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, font=dict(color=TEXT, family="Inter", size=11),
        annotations=[dict(text="ALLOCATION", x=0.5, y=0.5, showarrow=False,
                          font=dict(color=MUTED, size=9))],
    )
    st.plotly_chart(donut, width="stretch", config={"displayModeBar": False})

# ----------------------------------------------------------------------------
# DRAWDOWN (full width)
# ----------------------------------------------------------------------------
st.markdown('<div class="section">Drawdown · depth below prior peak</div>', unsafe_allow_html=True)
cumret = fm.cumulative_returns(port_growth)
dd = cumret / cumret.cummax() - 1
dd_pct = dd * 100
dd_min = float(dd_pct.min())
dd_span = abs(dd_min) if dd_min < 0 else 1.0
# Dynamic vertical framing keeps 0% from hugging the top on shallow drawdowns.
y_top = max(1.2, dd_span * 0.22)
y_bottom = min(-1.5, dd_min * 1.12)
worst_idx = dd_pct.idxmin()
worst_val = float(dd_pct.loc[worst_idx])
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=dd.index, y=dd_pct, fill="tozeroy",
  line=dict(color=DOWN, width=1.8), fillcolor="rgba(234,57,67,0.12)",
    hovertemplate="%{x|%b %d, %Y}<br>%{y:.1f}%<extra></extra>"))
fig2.add_trace(go.Scatter(
  x=[worst_idx], y=[worst_val], mode="markers",
  marker=dict(size=7, color=DOWN, line=dict(color=BG, width=1.2)),
  hovertemplate="Worst drawdown<br>%{x|%b %d, %Y}<br>%{y:.1f}%<extra></extra>",
  showlegend=False,
))
fig2.add_hrect(y0=y_bottom, y1=0, fillcolor="rgba(234,57,67,0.04)", line_width=0, layer="below")
fig2.update_layout(height=186, margin=dict(l=0, r=0, t=4, b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=MUTED, family="Inter"),
    xaxis=dict(showgrid=False, ticks="", color=MUTED, showspikes=True,
               spikemode="across", spikethickness=1, spikedash="dot",
               spikecolor="rgba(255,255,255,0.22)", spikesnap="cursor"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", ticksuffix="%",
          side="right", color=MUTED, range=[y_bottom, y_top],
          zeroline=True, zerolinecolor="rgba(255,255,255,0.28)", zerolinewidth=1),
    hovermode="x unified", hoverlabel=dict(bgcolor=SURFACE2, font_color=TEXT, bordercolor=BORDER))
st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

# ----------------------------------------------------------------------------
# AI SENTIMENT
# ----------------------------------------------------------------------------
if run_sentiment:
  st.markdown('<div class="section" style="margin-bottom:0.25rem">Oracle focus</div>', unsafe_allow_html=True)
  oc1, oc2 = st.columns([3, 1])
  with oc1:
    focus = st.segmented_control(
      "Oracle focus ticker",
      options=tickers,
      default=tickers[0],
      format_func=label,
      selection_mode="single",
      label_visibility="collapsed",
    ) or tickers[0]
  with oc2:
    with st.popover("How score works"):
      st.markdown("""
**Oracle score (selected ticker only)**

1. Pull recent headlines for the current Oracle Focus.
2. Use focus-tagged headlines when tags exist.
3. Score each headline in $[-1,+1]$.
4. Apply optional source-credibility weighting.
5. Average into one Oracle score.

Bands: Bullish >= 0.35 · Lean+ 0.10 to 0.35 · Neutral -0.10 to 0.10 · Lean- -0.35 to -0.10 · Bearish <= -0.35

**Focus vs weighting**

- Oracle Focus picks the ticker.
- Credibility weighting only reweights sources.
""")

  st.markdown(
    f'<div class="section" style="margin-bottom:0.15rem">'
    f'✦ Aurora Oracle · reading the news on {esc(label(focus))}</div>',
    unsafe_allow_html=True,
  )
  with st.spinner("The Oracle is reading the headlines…"):
    try:
      result = sent.analyze(focus, use_credibility=use_source_weighting)
    except TypeError as e:
      # Backward-compatible guard for stale/hot-reloaded modules that
      # don't yet accept the new keyword argument.
      if "use_credibility" in str(e):
        result = sent.analyze(focus)
        result["weighting"] = "source_credibility" if use_source_weighting else "none"
      else:
        raise

  is_claude = result["engine"] == "claude"
  engine_note = "Claude — a nuanced LLM read" if is_claude else "a finance-tuned VADER lexicon"
  score = result["score"]
  # Sentiment tone uses only green / gray / red — never gold.
  score_color = UP if score >= 0.05 else (DOWN if score <= -0.05 else MUTED)

  weighting_on = result.get("weighting") == "source_credibility"
  match_mode = result.get("match_mode", "fallback")
  match_count = int(result.get("match_count", 0) or 0)
  headline_count = int(result.get("headline_count", 0) or 0)
  match_value = (
    f"{match_count}/{headline_count} tagged" if match_mode == "strict" else "fallback"
  )
  # The long focus/weighting explanation now lives in the "How score works"
  # popover, so the section opens clean instead of leading with a paragraph.

  st.markdown(f"""
  <style>
    .oracle-feed {{ max-height: 380px; overflow-y: auto; padding-right: 6px; }}
    .oracle-feed::-webkit-scrollbar {{ width: 6px; }}
    .oracle-feed::-webkit-scrollbar-track {{ background: transparent; }}
    .oracle-feed::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.14); border-radius: 6px; }}
    .feed-item {{ display: flex; align-items: flex-start; gap: 0.6rem;
      padding: 0.55rem 0.72rem; margin-bottom: 0.5rem; background: {SURFACE};
      border: 1px solid {BORDER}; border-radius: 12px; }}
    .feed-item .fdot {{ width: 9px; height: 9px; border-radius: 50%;
      margin-top: 0.36rem; flex: none; }}
    .feed-head {{ color: {TEXT}; font-size: 0.82rem; line-height: 1.4; }}
    .feed-meta {{ font-size: 0.68rem; font-weight: 600; margin-top: 0.2rem; letter-spacing: 0.01em; }}
    .feed-score {{ color: {MUTED}; font-weight: 600; font-variant-numeric: tabular-nums;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .feed-src {{ color: {MUTED}; font-weight: 500; }}
    .feed-match {{ color: {GOLD}; font-weight: 700; font-size: 0.62rem;
      letter-spacing: 0.05em; text-transform: uppercase; }}
    .oracle-legend {{ color: {MUTED}; font-size: 0.68rem; margin: 0.1rem 0 0.5rem 0; }}
    .oracle-legend .ld {{ display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; margin: 0 0.25rem 0 0.7rem; }}
    .tone {{ font-weight: 700; font-size: 0.8rem; margin-top: 0.15rem; }}
    .okv-list {{ margin-top: 0.5rem; border-top: 1px solid {BORDER}; padding-top: 0.42rem; }}
    .okv {{ display: flex; justify-content: space-between; font-size: 0.7rem; padding: 0.13rem 0; }}
    .okv .k {{ color: {MUTED}; letter-spacing: 0.02em; }}
    .okv .v {{ color: {TEXT}; font-weight: 600; }}
  </style>
  """, unsafe_allow_html=True)

  c1, c2 = st.columns([0.95, 3.05], gap="small")
  with c1:
    # Hierarchy: dominant score, tone label, then a quiet key→value state list.
    kv = (
      f'<div class="okv"><span class="k">Focus</span>'
      f'<span class="v">{esc(label(focus))}</span></div>'
      f'<div class="okv"><span class="k">Credibility</span>'
      f'<span class="v">{"On" if weighting_on else "Off"}</span></div>'
      f'<div class="okv"><span class="k">Ticker match</span>'
      f'<span class="v">{esc(match_value)}</span></div>'
    )
    st.markdown(
      f'<div class="stat">'
      f'<div class="stat-label">Oracle score · average</div>'
      f'<div class="stat-value" style="color:{score_color}">{score:+.2f}</div>'
      f'<div class="tone" style="color:{score_color}">{result["label"]}</div>'
      f'<div class="okv-list">{kv}</div>'
      f'<div class="tkr-sub" style="margin-top:0.45rem">powered by {engine_note}</div>'
      f'</div>',
      unsafe_allow_html=True,
    )
  with c2:
    if result.get("summary"):
      st.markdown(
        f'<div class="news"><b style="color:{ACCENT2}">Oracle read:</b> {esc(result["summary"])}</div>',
        unsafe_allow_html=True,
      )

    detail = result.get("detail", [])
    if detail:
      st.markdown(
        f'<div class="oracle-legend">Each headline\'s tone:'
        f'<span class="ld" style="background:{UP}"></span>positive'
        f'<span class="ld" style="background:{MUTED}"></span>neutral'
        f'<span class="ld" style="background:{DOWN}"></span>negative'
        f' · focus match in gold</div>',
        unsafe_allow_html=True,
      )

      def tone_color(s: float | None) -> str:
        if s is None or -0.05 < s < 0.05:
          return MUTED
        return UP if s >= 0.05 else DOWN

      items = ""
      for d in detail:
        s = d.get("score")
        color = tone_color(s)
        if s is None:
          meta_inner = f'<span style="color:{MUTED}">part of the read</span>'
        else:
          # One calm line: tone (color) + score (subtle mono). Suppress fields
          # that carry no signal — unknown source, a 1.00x weight, the "BROAD" tag.
          bits = [
            f'<span style="color:{color}">{sent.tone_for(s)}</span>',
            f'<span class="feed-score">{s:+.2f}</span>',
          ]
          source = d.get("source")
          if source and str(source).strip().lower() not in ("", "unknown", "unknown source"):
            bits.append(f'<span class="feed-src">{esc(source)}</span>')
          cred = float(d.get("credibility", 1.0))
          if abs(cred - 1.0) > 0.005:
            bits.append(f'<span class="feed-src">{cred:.2f}x</span>')
          meta_inner = " · ".join(bits)
          if d.get("matches_focus"):        # gold, only on a real focus match
            meta_inner += f' <span class="feed-match">{esc(label(focus))}</span>'
        items += (
          f'<div class="feed-item"><div class="fdot" style="background:{color}"></div>'
          f'<div><div class="feed-head">{esc(d["headline"])}</div>'
          f'<div class="feed-meta">{meta_inner}</div></div></div>'
        )
      st.markdown(f'<div class="oracle-feed">{items}</div>', unsafe_allow_html=True)
    else:
      st.caption("No recent headlines came back for this asset right now.")

  # Oracle pulse — a plain-language, portfolio-ready panel for casual viewers.
  timeline = result.get("timeline", [])
  if detail:
    pos_n = sum(1 for d in detail if (d.get("score") is not None and d.get("score", 0.0) >= 0.05))
    neg_n = sum(1 for d in detail if (d.get("score") is not None and d.get("score", 0.0) <= -0.05))
    neu_n = max(len(detail) - pos_n - neg_n, 0)
    total_n = max(len(detail), 1)

    match_ratio = (match_count / headline_count) if headline_count > 0 else 0.0
    strength = abs(float(score))
    confidence = "High" if (headline_count >= 8 and match_ratio >= 0.45 and strength >= 0.18) else (
      "Medium" if (headline_count >= 4 and strength >= 0.08) else "Low"
    )
    conf_color = UP if confidence == "High" else (GOLD if confidence == "Medium" else MUTED)

    pulse_line = (
      f"Most coverage around {esc(label(focus))} is {esc(result['label'].lower())}. "
      f"{pos_n} positive, {neu_n} neutral, {neg_n} negative headlines in this read."
    )

    top_drivers = sorted(
      [d for d in detail if d.get("score") is not None],
      key=lambda d: abs(float(d.get("score", 0.0))),
      reverse=True,
    )[:3]

    mood_pos_w = 100.0 * pos_n / total_n
    mood_neu_w = 100.0 * neu_n / total_n
    mood_neg_w = 100.0 * neg_n / total_n

    st.markdown(f"""
    <style>
      .oracle-pulse {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px;
        padding: 0.72rem 0.82rem; margin-top: 0.56rem; }}
      .pulse-title {{ color: {MUTED}; font-size: 0.64rem; font-weight: 700;
        letter-spacing: 0.1em; text-transform: uppercase; }}
      .pulse-line {{ color: {TEXT}; font-size: 0.82rem; line-height: 1.38; margin-top: 0.28rem; }}
      .pulse-kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.45rem; margin-top: 0.56rem; }}
      .pulse-kpi {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px;
        padding: 0.48rem 0.52rem; }}
      .pulse-k {{ color: {MUTED}; font-size: 0.62rem; font-weight: 700;
        letter-spacing: 0.06em; text-transform: uppercase; }}
      .pulse-v {{ color: {TEXT}; font-size: 0.86rem; font-weight: 700; margin-top: 0.14rem; }}
      .pulse-mix {{ margin-top: 0.56rem; }}
      .pulse-track {{ width: 100%; height: 10px; border-radius: 999px; overflow: hidden;
        background: rgba(255,255,255,0.06); border: 1px solid {BORDER}; display: flex; }}
      .mix-pos {{ background: rgba(22,199,132,0.80); }}
      .mix-neu {{ background: rgba(139,140,166,0.70); }}
      .mix-neg {{ background: rgba(234,57,67,0.80); }}
      .pulse-meta {{ color: {MUTED}; font-size: 0.68rem; margin-top: 0.3rem; }}
      .pulse-list {{ margin-top: 0.52rem; border-top: 1px solid {BORDER}; padding-top: 0.42rem; }}
      .pulse-item {{ color: {TEXT}; font-size: 0.76rem; line-height: 1.36; margin-bottom: 0.3rem; }}
      .pulse-tag {{ color: {MUTED}; font-size: 0.65rem; font-weight: 600; margin-right: 0.35rem; }}
      @media (max-width: 760px) {{
        .pulse-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section" style="margin-top:0.6rem">Oracle pulse</div>', unsafe_allow_html=True)
    st.markdown(
      f'<div class="oracle-pulse">'
      f'<div class="pulse-title">What this means right now</div>'
      f'<div class="pulse-line">{pulse_line}</div>'
      f'<div class="pulse-kpis">'
      f'  <div class="pulse-kpi"><div class="pulse-k">Coverage</div><div class="pulse-v">{headline_count} headlines</div></div>'
      f'  <div class="pulse-kpi"><div class="pulse-k">Match quality</div><div class="pulse-v">{match_value}</div></div>'
      f'  <div class="pulse-kpi"><div class="pulse-k">Signal confidence</div><div class="pulse-v" style="color:{conf_color}">{confidence}</div></div>'
      f'</div>'
      f'<div class="pulse-mix">'
      f'  <div class="pulse-track">'
      f'    <div class="mix-pos" style="width:{mood_pos_w:.2f}%"></div>'
      f'    <div class="mix-neu" style="width:{mood_neu_w:.2f}%"></div>'
      f'    <div class="mix-neg" style="width:{mood_neg_w:.2f}%"></div>'
      f'  </div>'
      f'  <div class="pulse-meta">Mood mix: {pos_n} positive · {neu_n} neutral · {neg_n} negative</div>'
      f'</div>'
      f'</div>',
      unsafe_allow_html=True,
    )

    if top_drivers:
      items = ""
      for i, d in enumerate(top_drivers, start=1):
        sc = float(d.get("score", 0.0))
        tone = sent.tone_for(sc)
        items += (
          f'<div class="pulse-item">'
          f'<span class="pulse-tag">Driver {i}</span>'
          f'<span style="color:{UP if sc >= 0.05 else (DOWN if sc <= -0.05 else MUTED)}">{tone} {sc:+.2f}</span>'
          f' · {esc(d.get("headline", ""))}'
          f'</div>'
        )
      st.markdown(f'<div class="oracle-pulse" style="margin-top:0.42rem"><div class="pulse-title">Top drivers</div><div class="pulse-list">{items}</div></div>', unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# DATA PROVENANCE + DISCLAIMER
# ----------------------------------------------------------------------------
_generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
st.markdown(
    f'<div style="color:{MUTED};font-size:0.7rem;letter-spacing:0.015em;margin-top:0.5rem;">'
    f'Data: Yahoo Finance · {len(value_series)} trading days · generated {_generated}</div>',
    unsafe_allow_html=True,
)
st.caption("For learning / portfolio use only — not financial advice.")