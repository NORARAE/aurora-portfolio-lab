# Aurora Portfolio Lab

Aurora Portfolio Lab is an interactive multi-asset portfolio dashboard built with
Python and Streamlit. It combines live market data, portfolio analytics, and a
news-sentiment layer in a compact interface designed for fast exploration.

This project is presented as an engineering and product portfolio piece. The goal
is to show practical decision-making across data handling, finance metrics,
interactive visualization, and user experience.

**Disclaimer:** educational and portfolio use only. Not financial advice.

## Core capabilities

- Pulls live price data for equities and crypto tickers with `yfinance`
- Supports portfolio construction by percentage or dollar allocation
- Computes risk and performance metrics (including drawdown-oriented analysis)
- Visualizes portfolio value, allocation, and risk in interactive Plotly charts
- Adds an "Oracle" sentiment layer with source-aware scoring and headline detail

## Why this is portfolio-relevant

- Separates concerns across UI, metrics, and sentiment modules
- Uses defensible finance calculations rather than display-only heuristics
- Handles real-world data issues (missing symbols, sparse news, optional AI keys)
- Balances technical depth with product clarity for non-technical stakeholders

## Stack

- Python
- Streamlit
- Pandas
- Plotly
- yfinance
- VADER sentiment (+ optional Anthropic Claude integration)

## Repository layout

```
.
|- app.py
|- finance_metrics.py
|- sentiment.py
|- requirements.txt
|- .streamlit/config.toml
|- README.md
`- CLAUDE.md
```

## Local setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Optional sentiment upgrade

To enable Claude-powered sentiment summaries, add this in
`.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Without this key, the app uses the built-in VADER flow.
