"""
sentiment.py
------------
The 'something new' part of the project: reading recent news headlines for a
stock and scoring how positive or negative the coverage is. This is what
makes the dashboard feel forward-thinking rather than just another chart.

Two engines, and the app picks the best one available automatically:

  1. VADER (default, always works, zero setup) — a fast rule-based sentiment
     model that's genuinely good at short, punchy text like headlines.

  2. Claude (optional, richer) — if you add an ANTHROPIC_API_KEY, we ask an
     LLM to read the headlines and give a nuanced market-sentiment read plus
     a one-line summary. This is the 'AI sentiment' upgrade and it's a great
     thing to demo, but the app runs perfectly fine without it.

Teaching note: designing a feature so it *degrades gracefully* (works with
nothing, gets better with an API key) is a real engineering skill. Recruiters
notice it.
"""

from __future__ import annotations

import datetime as dt
import os

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# VADER is trained on general/social text, so it's deaf to market jargon —
# out of the box it scores "Nvidia soars on earnings beat" as neutral, which
# is useless for finance. We patch its lexicon with domain words (scores run
# -4 to +4) so it actually reacts to how markets talk. Extend this freely.
_FINANCE_LEXICON = {
    # bullish
    "soars": 3.0, "soar": 3.0, "surges": 2.8, "surge": 2.8, "rally": 2.4,
    "rallies": 2.4, "beat": 2.2, "beats": 2.2, "jumps": 2.4, "jump": 2.2,
    "gains": 1.8, "climb": 1.8, "climbs": 1.8, "upgrade": 2.4, "upgraded": 2.4,
    "outperform": 2.2, "record": 1.8, "profit": 1.6, "growth": 1.6,
    "bullish": 2.6, "rebound": 1.8, "soaring": 3.0, "boom": 2.2, "top": 1.2,
    # bearish
    "plunges": -3.0, "plunge": -3.0, "plummets": -3.2, "crash": -3.4,
    "crashes": -3.4, "tumbles": -2.6, "slumps": -2.4, "slump": -2.4,
    "falls": -1.8, "fall": -1.6, "drops": -1.8, "sinks": -2.4, "misses": -2.2,
    "miss": -2.0, "downgrade": -2.4, "downgraded": -2.4, "cuts": -1.6,
    "probe": -1.8, "lawsuit": -2.0, "bearish": -2.6, "warns": -1.8,
    "warning": -1.8, "loss": -1.8, "losses": -1.8, "recall": -2.0,
    "layoffs": -2.2, "bankruptcy": -3.2, "selloff": -2.2, "slides": -1.8,
}

# Lightweight credibility weights for common finance/business outlets.
# 1.00 means neutral weight; above/below nudges influence modestly.
_SOURCE_CREDIBILITY = {
    "reuters": 1.20,
    "associated press": 1.15,
    "ap": 1.15,
    "bloomberg": 1.15,
    "the wall street journal": 1.12,
    "wall street journal": 1.12,
    "financial times": 1.10,
    "marketwatch": 1.05,
    "cnbc": 1.02,
    "investing.com": 0.98,
    "yahoo finance": 0.98,
    "benzinga": 0.95,
    "motley fool": 0.92,
    "seeking alpha": 0.92,
}

_vader = SentimentIntensityAnalyzer()
_vader.lexicon.update(_FINANCE_LEXICON)


def _related_tickers_from_item(item: dict) -> list[str]:
    """Extract related tickers from Yahoo payload when available."""
    raw = item.get("relatedTickers")
    if isinstance(raw, list):
        return [str(x).upper() for x in raw if x]
    content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
    raw_content = content.get("relatedTickers")
    if isinstance(raw_content, list):
        return [str(x).upper() for x in raw_content if x]
    return []


def _headline_matches_focus(headline: str, ticker: str, related_tickers: list[str]) -> bool:
    """Determine if a headline is clearly tied to the selected focus ticker."""
    tk = ticker.upper()
    base = tk.replace("-USD", "")
    if related_tickers:
        rel = set(related_tickers)
        return tk in rel or base in rel
    up = headline.upper()
    return tk in up or base in up


def _parse_publish_time(item: dict) -> dt.datetime | None:
    """Best-effort parse for Yahoo news timestamps into UTC-naive datetimes."""
    raw = (
        item.get("providerPublishTime")
        or item.get("publishTime")
        or item.get("publishedAt")
        or item.get("content", {}).get("pubDate")
    )
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        try:
            return dt.datetime.utcfromtimestamp(raw)
        except Exception:
            return None

    if isinstance(raw, str):
        text = raw.strip()
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = dt.datetime.fromisoformat(text)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
            return parsed
        except Exception:
            return None

    return None


def _source_from_item(item: dict) -> str | None:
    """Pull a publisher/source label from Yahoo's shifting payload shape."""
    content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
    provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
    return (
        item.get("publisher")
        or provider.get("displayName")
        or content.get("provider")
        or item.get("source")
    )


def _credibility_for(source: str | None) -> float:
    """Map source name to a modest weight; unknown sources default to 1.0."""
    if not source:
        return 1.0
    key = source.strip().lower()
    if key in _SOURCE_CREDIBILITY:
        return _SOURCE_CREDIBILITY[key]
    for name, weight in _SOURCE_CREDIBILITY.items():
        if name in key:
            return weight
    return 1.0


def _build_timeline(detail: list[dict]) -> list[dict]:
    """Aggregate headline sentiment by day for the trend chart."""
    buckets: dict[dt.date, list[float]] = {}
    for d in detail:
        if d.get("score") is None:
            continue
        published_at = d.get("published_at")
        if published_at:
            try:
                day = dt.datetime.fromisoformat(published_at).date()
            except Exception:
                day = dt.date.today()
        else:
            day = dt.date.today()
        buckets.setdefault(day, []).append(float(d["score"]))

    timeline = []
    for day in sorted(buckets):
        vals = buckets[day]
        timeline.append({
            "date": day.isoformat(),
            "score": sum(vals) / len(vals),
            "count": len(vals),
        })
    return timeline


def fetch_news_items(ticker: str, limit: int = 24) -> list[dict]:
    """Fetch headline + source + publish timestamp for downstream scoring/charting."""
    import yfinance as yf

    items: list[dict] = []
    try:
        news = yf.Ticker(ticker).news or []
        for item in news:
            title = item.get("title") or item.get("content", {}).get("title")
            if not title:
                continue
            source = _source_from_item(item)
            published = _parse_publish_time(item)
            related = _related_tickers_from_item(item)
            items.append({
                "headline": title,
                "source": source,
                "published_at": published.isoformat() if published else None,
                "related_tickers": related,
                "matches_focus": _headline_matches_focus(title, ticker, related),
            })
    except Exception:
        pass
    return items[:limit]


def fetch_headlines(ticker: str, limit: int = 8) -> list[str]:
    """
    Pull recent news headlines for a ticker via yfinance.
    Yahoo's news payload shape changes now and then, so we defend against it
    and just return whatever titles we can find (empty list if none).
    """
    return [n["headline"] for n in fetch_news_items(ticker, limit=limit)]


def score_vader(headlines: list[str] | list[dict], use_credibility: bool = True) -> dict:
    """
    Score each headline from -1 (very negative) to +1 (very positive) and
    average them. Returns the overall score, a label, and per-headline detail
    so the UI can show the receipts.
    """
    if not headlines:
        return {"engine": "vader", "score": 0.0, "label": "No coverage", "detail": []}

    detail = []
    for h in headlines:
        if isinstance(h, dict):
            headline = str(h.get("headline", "")).strip()
            source = h.get("source")
            published_at = h.get("published_at")
        else:
            headline = str(h).strip()
            source = None
            published_at = None

        if not headline:
            continue

        raw = _vader.polarity_scores(headline)["compound"]
        credibility = _credibility_for(source) if use_credibility else 1.0
        weighted = max(-1.0, min(1.0, raw * credibility))
        detail.append({
            "headline": headline,
            "score": weighted,
            "raw_score": raw,
            "credibility": credibility,
            "source": source,
            "published_at": published_at,
            "related_tickers": h.get("related_tickers", []) if isinstance(h, dict) else [],
            "matches_focus": bool(h.get("matches_focus", False)) if isinstance(h, dict) else False,
        })

    if not detail:
        return {"engine": "vader", "score": 0.0, "label": "No coverage", "detail": [], "timeline": []}

    avg = sum(d["score"] for d in detail) / len(detail)
    return {
        "engine": "vader",
        "score": avg,
        "label": _label_for(avg),
        "detail": detail,
        "timeline": _build_timeline(detail),
        "weighting": "source_credibility" if use_credibility else "none",
    }


def score_claude(headlines: list[str], ticker: str) -> dict | None:
    """
    Optional richer read using Claude. Returns None if no API key is set,
    so the caller can fall back to VADER. Requires ANTHROPIC_API_KEY in the
    environment or Streamlit secrets.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not headlines:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        joined = "\n".join(f"- {h}" for h in headlines)
        prompt = (
            f"Here are recent news headlines about {ticker}:\n\n{joined}\n\n"
            "Assess the overall market sentiment these headlines convey toward "
            "the stock. Respond in exactly this format:\n"
            "SCORE: <a number from -1.0 to 1.0>\n"
            "SUMMARY: <one concise sentence>"
        )
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()

        # Parse the two labelled lines out of the response.
        score, summary = 0.0, ""
        for line in text.splitlines():
            if line.upper().startswith("SCORE:"):
                try:
                    score = float(line.split(":", 1)[1].strip())
                except ValueError:
                    score = 0.0
            elif line.upper().startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()

        return {
            "engine": "claude",
            "score": score,
            "label": _label_for(score),
            "summary": summary,
            "detail": [{"headline": h, "score": None} for h in headlines],
        }
    except Exception:
        # Any API problem: fall back silently to VADER upstream.
        return None


def analyze(
    ticker: str,
    limit: int = 8,
    use_credibility: bool = True,
    **_unused_kwargs,
) -> dict:
    """
    Top-level entry point the app calls. Fetches headlines, prefers Claude if
    available, otherwise uses VADER. Always returns a result dict.
    """
    news_items = fetch_news_items(ticker, limit=max(limit, 24))
    matched_items = [n for n in news_items if n.get("matches_focus")]
    selected_items = (matched_items or news_items)[:limit]
    headlines = [n["headline"] for n in selected_items]
    vader = score_vader(selected_items, use_credibility=use_credibility)
    vader["focus_ticker"] = ticker
    vader["match_mode"] = "strict" if matched_items else "fallback"
    vader["match_count"] = len(matched_items)
    vader["headline_count"] = len(selected_items)
    claude = score_claude(headlines, ticker)
    if claude:
        # Keep Claude's overall read, but expose VADER-scored detail/timeline so
        # the UI can still show per-headline tone and trend context.
        claude["detail"] = vader.get("detail", [])
        claude["timeline"] = vader.get("timeline", [])
        claude["weighting"] = "source_credibility" if use_credibility else "none"
        claude["focus_ticker"] = ticker
        claude["match_mode"] = vader.get("match_mode", "fallback")
        claude["match_count"] = vader.get("match_count", 0)
        claude["headline_count"] = vader.get("headline_count", len(headlines))
        return claude
    return vader


def _label_for(score: float) -> str:
    """Turn a number into a human word for the badge in the UI."""
    if score >= 0.35:
        return "Bullish"
    if score >= 0.10:
        return "Leaning positive"
    if score > -0.10:
        return "Neutral"
    if score > -0.35:
        return "Leaning negative"
    return "Bearish"


def tone_for(score: float) -> str:
    """Plain-English tone for a SINGLE headline. Deliberately simpler words than
    the portfolio-level Bullish/Bearish label above — 'Positive/Negative' reads
    more naturally line-by-line in the news feed."""
    if score >= 0.35:
        return "Very positive"
    if score >= 0.05:
        return "Positive"
    if score > -0.05:
        return "Neutral"
    if score > -0.35:
        return "Negative"
    return "Very negative"
