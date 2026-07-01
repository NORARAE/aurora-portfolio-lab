# ✦ Aurora Portfolio Lab

An interactive stock-portfolio dashboard built in Python. Type in tickers
(stocks or crypto), set your investment and how it's split, and get live
market data, real finance risk metrics, and an **AI read on the news** — all
in a dark, aurora-glow UI.

Built as a portfolio piece to show off data handling, finance fundamentals,
data viz, and a forward-thinking AI feature — with a live, clickable demo.

**Not financial advice. Learning/portfolio project only.**

---

## What it does

- **Live data** for any ticker(s) via `yfinance` (free, public).
- **Risk metrics** computed from scratch: total & annualized return,
  annualized volatility, Sharpe ratio, and max drawdown.
- **Charts**: price with 50/200-day moving averages, portfolio growth-of-$1,
  and a drawdown chart.
- **Aurora Oracle** (AI news sentiment): reads recent headlines and scores
  their tone in a scrollable, color-coded feed. Works offline with a
  finance-tuned VADER lexicon, and upgrades to a richer **Claude-powered**
  read if you add an API key.
- **Investment & allocation**: set a "play money" amount, then split it across
  holdings by percent or by dollars — with a live allocation bar.

## Tech & skills demonstrated

`pandas` time-series · finance math · `plotly` interactive charts ·
API data fetching · `streamlit` web app · graceful AI integration · clean,
modular, documented code.

## Project layout

```
finance-dashboard/
├── app.py               # UI + flow (the front of house)
├── finance_metrics.py   # all the finance math, heavily commented
├── sentiment.py         # AI sentiment (VADER default, Claude optional)
├── requirements.txt
├── .streamlit/config.toml  # theme (committed); secrets.toml is git-ignored
├── .gitignore
├── README.md
└── CLAUDE.md            # guide for extending this with Claude Code
```

## Run it locally

Requires **Python 3.10+** (built and tested on Python 3.13 — the latest
`yfinance` needs 3.10 or newer).

```bash
# 1. (optional) create a virtual environment
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. launch
streamlit run app.py
```

It opens at `http://localhost:8501`.

## Optional: turn on Claude-powered sentiment

Create `.streamlit/secrets.toml` (already git-ignored):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Without it, the app happily uses VADER instead — nothing breaks.

## Deploy free (get a live link for your resume)

1. Push this folder to a **public GitHub repo**.
2. Go to **share.streamlit.io**, sign in with GitHub, and pick the repo.
3. Set the main file to `app.py` and deploy.
4. (Optional) add `ANTHROPIC_API_KEY` under the app's **Secrets** settings.

You'll get a public URL like `https://your-app.streamlit.app` to share.

## Ideas to extend

Benchmark vs the S&P 500 · a correlation heatmap between holdings ·
efficient-frontier optimizer · downloadable PDF report · caching news to
show sentiment over time. See `CLAUDE.md` for how to tackle these with
Claude Code.
