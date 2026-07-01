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
  html, body, [class*="css"], .stMarkdown, p, span, div {{
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    font-feature-settings: 'tnum';
  }}
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

  section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
  [data-testid="stSidebar"] .stButton button {{ background: {SURFACE2}; border: 1px solid {BORDER};
    color: {TEXT}; border-radius: 10px; font-size: 0.72rem; font-weight: 600; padding: 0.18rem 0; }}
  [data-testid="stSidebar"] .stButton button:hover {{ border-color: {ACCENT}; color: {ACCENT2}; }}

  /* Phone tuning */
  @media (max-width: 640px) {{
    .hero-value {{ font-size: 1.92rem; }}
    .hero {{ padding: 0.95rem 0.92rem 0.44rem 0.92rem; }}
    .block-container {{ padding-left: 0.8rem; padding-right: 0.8rem; }}
    .stat-value {{ font-size: 1.16rem; }}
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
        for t in tickers:
            st.session_state[f"pct_{t}"] = round(100 / n)


def open_invest_modal():
    """Reopen the investment dialog (button callback)."""
    st.session_state.force_open_invest_modal = True


@st.dialog("Set your investment")
def investment_dialog():
    """First-visit (and on-demand) modal for the master investment amount — the
    single source of truth the whole dashboard scales from. It's 'play money':
    set it here, then nudge it live with the slider on the page."""
    st.write("How much are you putting to work? It's play money — you can slide "
             "it around on the dashboard anytime.")
    v = st.number_input("Amount ($)", min_value=500, max_value=1_000_000,
                        value=int(st.session_state.get("invested", 10_000)), step=500)
    if st.button("Start investing →", type="primary", width="stretch"):
        st.session_state.invested = int(v)
        st.session_state.invest_set = True
        st.session_state.invest_prompt_seen = True
        st.rerun()


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
if "tickers_text" not in st.session_state:
    st.session_state.tickers_text = "AAPL, MSFT, NVDA"
st.session_state.setdefault("invested", 10_000)   # master portfolio amount ($)
st.session_state.setdefault("invest_set", False)
st.session_state.setdefault("invest_prompt_seen", False)
st.session_state.setdefault("force_open_invest_modal", False)

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
        for t in tickers:
            st.session_state.setdefault(f"pct_{t}", round(100 / n_hold))
        pcts = {t: st.slider(label(t), 0, 100, key=f"pct_{t}", format="%d%%") for t in tickers}
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
            st.caption(f"Splitting {money(amount)} · entered {entered}%"
                       + ("" if entered == 100 else " → auto-balanced to 100%"))
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
# INVESTMENT — the master amount. Modal onboarding + a live "play money" slider.
# This single value is what the whole dashboard scales from.
# ----------------------------------------------------------------------------
if st.session_state.pop("force_open_invest_modal", False):
  investment_dialog()          # explicit on-demand open from the ✎ Edit button
elif (not st.session_state.get("invest_set")) and (not st.session_state.get("invest_prompt_seen")):
  st.session_state.invest_prompt_seen = True
  investment_dialog()          # first visit only

st.markdown('<div class="section" style="margin-bottom:0.25rem">'
            'Investment · slide to explore</div>', unsafe_allow_html=True)
# Let the slider's ceiling grow if the modal set a bigger number, so it never
# clamps a valid amount (Streamlit errors if a value exceeds the slider max).
inv_max = max(100_000, int(st.session_state.get("invested", 10_000)))
iv1, iv2 = st.columns([5, 1])
with iv1:
    st.slider("Investment", min_value=500, max_value=inv_max, step=500,
              key="invested", label_visibility="collapsed")
with iv2:
    st.button("✎ Edit", on_click=open_invest_modal, width="stretch",
              help="Type an exact amount.")

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
# HOLDINGS (full width, stacks naturally)
# ----------------------------------------------------------------------------
st.markdown('<div class="section">Holdings · this window</div>', unsafe_allow_html=True)
per = fm.per_ticker_returns(view)
total_w = sum(weights[t] for t in per if t in weights) or 1
rows = ""
for t, r in sorted(per.items(), key=lambda kv: -kv[1]):
    w = weights.get(t, 0) / total_w
    cls = "up-t" if r >= 0 else "down-t"
    rows += (f'<div class="holding"><div><div class="tkr">{esc(label(t))}</div>'
             f'<div class="tkr-sub">{w*100:.0f}% of portfolio</div></div>'
             f'<div class="stat-value {cls}" style="font-size:1.15rem">{pct(r)}</div></div>')
st.markdown(rows, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# DRAWDOWN (full width)
# ----------------------------------------------------------------------------
st.markdown('<div class="section">Drawdown · depth below prior peak</div>', unsafe_allow_html=True)
cumret = fm.cumulative_returns(port_growth)
dd = cumret / cumret.cummax() - 1
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=dd.index, y=dd * 100, fill="tozeroy",
    line=dict(color=DOWN, width=1.6), fillcolor="rgba(234,57,67,0.10)",
    hovertemplate="%{x|%b %d, %Y}<br>%{y:.1f}%<extra></extra>"))
fig2.update_layout(height=186, margin=dict(l=0, r=0, t=4, b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=MUTED, family="Inter"),
    xaxis=dict(showgrid=False, ticks="", color=MUTED, showspikes=True,
               spikemode="across", spikethickness=1, spikedash="dot",
               spikecolor="rgba(255,255,255,0.22)", spikesnap="cursor"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", ticksuffix="%",
               side="right", color=MUTED),
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
**Oracle score (for selected ticker only)**

1. Pull recent headlines for the selected ticker.
2. Keep headlines tagged to the focus ticker when tags exist.
3. Score each headline on $[-1, +1]$ (VADER compound).
4. Apply optional source-credibility weighting.
5. Average into one Oracle score.

Label bands:

- Bullish: >= 0.35
- Leaning positive: 0.10 to 0.35
- Neutral: -0.10 to 0.10
- Leaning negative: -0.35 to -0.10
- Bearish: <= -0.35
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
  cls = "up-t" if score >= 0.05 else ("down-t" if score <= -0.05 else "gold-t")

  weighting_on = result.get("weighting") == "source_credibility"
  weighting_label = "Credibility weighting: ON" if weighting_on else "Credibility weighting: OFF"
  match_mode = result.get("match_mode", "fallback")
  match_count = int(result.get("match_count", 0) or 0)
  headline_count = int(result.get("headline_count", 0) or 0)
  focus_badge = f"Focus: {label(focus)}"
  match_label = (
    f"Ticker match: {match_count}/{headline_count} tagged"
    if match_mode == "strict" else
    "Ticker match: fallback (tag data unavailable)"
  )
  weighting_desc = (
    f"Oracle Focus controls ticker selection. For {label(focus)}, Aurora scores only focus-matched headlines "
    "when tags are available. Source credibility weighting only changes weighting, not ticker focus."
    if weighting_on else
    f"Oracle Focus controls ticker selection. For {label(focus)}, Aurora scores only focus-matched headlines "
    "when tags are available. Credibility weighting is OFF, so each source is weighted equally."
  )
  st.caption(f"{weighting_desc} Powered by {engine_note}.")

  st.markdown(f"""
  <style>
    .oracle-feed {{ max-height: 360px; overflow-y: auto; padding-right: 6px; }}
    .oracle-feed::-webkit-scrollbar {{ width: 6px; }}
    .oracle-feed::-webkit-scrollbar-track {{ background: transparent; }}
    .oracle-feed::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.14); border-radius: 6px; }}
    .oracle-note {{ color: {MUTED}; font-size: 0.69rem; letter-spacing: 0.015em; }}
    .oracle-panel {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
      padding: 0.6rem 0.75rem; margin-bottom: 0.45rem; }}
    .feed-item {{ display: flex; align-items: flex-start; gap: 0.6rem;
    padding: 0.45rem 0.62rem; margin-bottom: 0.38rem; background: {SURFACE};
    border: 1px solid {BORDER}; border-radius: 12px; }}
    .feed-item .fdot {{ width: 9px; height: 9px; border-radius: 50%;
    margin-top: 0.32rem; flex: none; }}
    .feed-head {{ color: {TEXT}; font-size: 0.8rem; line-height: 1.28; }}
    .feed-meta {{ font-size: 0.65rem; font-weight: 700; margin-top: 0.14rem; letter-spacing: 0.015em; }}
    .oracle-legend {{ color: {MUTED}; font-size: 0.68rem; margin: 0.1rem 0 0.45rem 0; }}
    .oracle-legend .ld {{ display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; margin: 0 0.25rem 0 0.7rem; }}
    .feed-src {{ color: {MUTED}; opacity: 0.9; }}
    .feed-match {{ color: {GOLD}; opacity: 0.95; }}
  </style>
  """, unsafe_allow_html=True)

  c1, c2 = st.columns([0.95, 3.05], gap="small")
  with c1:
    st.markdown(
      f'<div class="stat"><div class="stat-label">Oracle score · average</div>'
      f'<div class="stat-value {cls}">{score:+.2f}</div>'
      f'<div style="margin-top:0.5rem"><span class="badge">{result["label"]}</span></div>'
      f'<div style="margin-top:0.45rem"><span class="badge">{focus_badge}</span></div>'
      f'<div style="margin-top:0.45rem"><span class="badge">{weighting_label}</span></div>'
      f'<div style="margin-top:0.45rem"><span class="badge">{match_label}</span></div>'
      f'<div class="tkr-sub" style="margin-top:0.48rem">powered by {engine_note}</div></div>',
      unsafe_allow_html=True,
    )
  with c2:
    if result.get("summary"):
      st.markdown(
        f'<div class="news"><b class="gold-t">Oracle read:</b> {esc(result["summary"])} </div>',
        unsafe_allow_html=True,
      )

    rc1, rc2 = st.columns([1.05, 1.95], gap="small")
    with rc1:
      st.markdown('<div class="oracle-panel"><div class="oracle-note">Sentiment trend</div></div>', unsafe_allow_html=True)
      timeline = result.get("timeline", [])
      if timeline:
        tdf = pd.DataFrame(timeline)
        tdf["date"] = pd.to_datetime(tdf["date"])
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
          x=tdf["date"],
          y=tdf["score"],
          mode="lines+markers",
          line=dict(color=ACCENT2, width=2.2),
          marker=dict(size=6, color=ACCENT),
          customdata=tdf[["count"]],
          hovertemplate="%{x|%b %d, %Y}<br>score %{y:+.2f}<br>%{customdata[0]} headlines<extra></extra>",
        ))
        fig3.update_layout(
          height=162,
          margin=dict(l=0, r=0, t=6, b=0),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color=MUTED, family="Inter"),
          xaxis=dict(showgrid=False, ticks="", color=MUTED),
          yaxis=dict(
            range=[-1, 1],
            dtick=0.5,
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color=MUTED,
          ),
          hovermode="x unified",
          hoverlabel=dict(bgcolor=SURFACE2, font_color=TEXT, bordercolor=BORDER),
        )
        st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
      else:
        st.caption("Trend appears once recent headline dates are available.")

    with rc2:
      detail = result.get("detail", [])
      if detail:
        st.markdown(
          f'<div class="oracle-legend">Each headline\'s tone:'
          f'<span class="ld" style="background:{UP}"></span>positive'
          f'<span class="ld" style="background:{MUTED}"></span>neutral'
          f'<span class="ld" style="background:{DOWN}"></span>negative'
          f' · matching shown in gold</div>',
          unsafe_allow_html=True,
        )

        def tone_color(s: float | None) -> str:
          if s is None or -0.05 < s < 0.05:
            return MUTED
          return UP if s >= 0.05 else DOWN

        items = ""
        focus_label = esc(label(focus))
        for d in detail:
          s = d.get("score")
          color = tone_color(s)
          source = esc(d.get("source") or "Unknown source")
          cred = float(d.get("credibility", 1.0))
          match_text = "MATCH" if d.get("matches_focus") else "BROAD"
          if s is None:
            meta = f'<div class="feed-meta" style="color:{MUTED}">part of the read</div>'
          else:
            meta = (
              f'<div class="feed-meta" style="color:{color}">'
              f'{sent.tone_for(s)} · {s:+.2f} '
              f'<span class="feed-src">({source} · {cred:.2f}x)</span> '
              f'<span class="feed-match">[{match_text} · {focus_label}]</span></div>'
            )
          items += (
            f'<div class="feed-item"><div class="fdot" style="background:{color}"></div>'
            f'<div><div class="feed-head">{esc(d["headline"])}</div>{meta}</div></div>'
          )
        st.markdown(f'<div class="oracle-feed">{items}</div>', unsafe_allow_html=True)
      else:
        st.caption("No recent headlines came back for this asset right now.")

st.write("")
st.caption("For learning / portfolio use only — not financial advice.")