# CLAUDE.md — agent guide for this project

This file orients Claude Code (and any AI agent) working in this repo. Read it
first before making changes.

## What this project is

**Aurora Portfolio Lab** — a Streamlit dashboard that pulls live stock data,
computes finance risk metrics, and shows an AI read on news sentiment. It's a
portfolio piece, so **code clarity and a polished look matter as much as
correctness.** The owner is learning from this repo, so favor readable,
well-commented code over clever one-liners, and explain non-obvious finance or
data concepts in comments.

## Architecture (keep this separation)

- `app.py` — **UI and flow only.** Page setup, inputs, layout, charts. It
  should orchestrate, not calculate. If you're writing math here, it probably
  belongs in `finance_metrics.py`.
- `finance_metrics.py` — **pure functions** that take pandas data and return
  numbers/Series. No Streamlit imports here. Easy to test in isolation.
- `sentiment.py` — news fetching + sentiment scoring. Two engines: VADER
  (default, offline) and Claude (optional, via `ANTHROPIC_API_KEY`). New
  sentiment logic goes here, not in `app.py`.
- `paper_broker.py` — **pure functions** for the paper-trading game:
  buy/sell, cost basis, P/L, account summaries. Zero Streamlit imports.
  New trading rules go here, not in `app.py`. Full pytest coverage in
  `tests/test_paper_broker.py`.

When adding a feature, ask: is it *math* (→ finance_metrics), *AI/news* (→
sentiment), *trading logic* (→ paper_broker), or *presentation* (→ app)?
Put it in the right file.

## How to run / verify

```bash
pip install -r requirements.txt
streamlit run app.py            # opens http://localhost:8501
python -m py_compile app.py finance_metrics.py sentiment.py   # quick syntax check
```

There's no test suite yet — **adding one (pytest against `finance_metrics.py`)
is a welcome first contribution.** Those functions are pure and easy to test.

## Design tokens (do not drift from these)

The look is inherited from the owner's "Node Bloom" piece — a matching
portfolio set. Reuse these exact values:

| Token   | Hex       | Use                          |
|---------|-----------|------------------------------|
| BG      | `#0a0612` | near-black purple background  |
| PANEL   | `#140b22` | cards / sidebar              |
| GOLD    | `#f5c451` | the signature + highlights   |
| CYAN    | `#4de1d0` | primary accent / positive    |
| VIOLET  | `#a78bfa` | secondary accent             |
| TEXT    | `#e6e9f5` | body text (high contrast)    |
| MUTED   | `#8b90b5` | labels                       |
| (neg)   | `#ff6b8a` | losses / drawdown            |

Type is **JetBrains Mono**. Charts use the `style_fig()` helper in `app.py` —
route every new Plotly chart through it so styling stays consistent. Keep
contrast high (a lesson learned on Node Bloom: dim text read badly on mobile).

The gold "designed + coded by Nora Genetti" signature is intentional — keep it.

## Conventions

- Comment the *why* and the *finance meaning*, not just the *what*.
- Keep functions small and single-purpose.
- Never commit secrets. API keys go in `.streamlit/secrets.toml` (git-ignored).
- Handle network/data failures gracefully — the app should degrade, not crash
  (see how `sentiment.py` falls back from Claude to VADER).
- Cache expensive data calls with `@st.cache_data` (see `load_prices`).

## Task backlog (good next steps)

1. **Benchmark comparison** — overlay SPY on the growth-of-$1 chart so users
   see the portfolio vs the market. (math → finance_metrics, draw → app)
2. **Correlation heatmap** — how correlated are the holdings? (Plotly heatmap)
3. **pytest suite** for `finance_metrics.py` with a few known-value cases.
4. **Sentiment-over-time** — cache daily sentiment and chart the trend.
5. **PDF export** of the current view for a shareable report.
6. **Efficient frontier** — plot risk/return of weight combinations.

When you pick one up, follow the architecture split above and match the design
tokens. Leave the code a little clearer than you found it.
