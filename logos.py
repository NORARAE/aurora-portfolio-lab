"""
logos.py — asset logo resolution with a bulletproof monogram fallback.

The holdings display should NEVER show a broken image. So every path here
degrades gracefully to `None`, and the renderer turns `None` into a first-class
gradient monogram badge (not an error state).

Two logo sources:
  - Crypto: bundled CC0 icons in assets/icons/{symbol}.png — no network call.
  - Stocks: the quikturn logo API, keyed by the company's web domain (resolved
    from yfinance). Needs QUIKTURN_KEY in st.secrets; with no key (or any
    failure) it returns None and the caller draws a monogram instead.

app.py imports these three functions and does nothing else — no requests calls
and no badge HTML live in the UI layer.
"""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
import yfinance as yf

# Bundled crypto icons live next to this module, under assets/icons/.
_ICON_DIR = Path(__file__).parent / "assets" / "icons"

# quikturn logo service. We hit it as {ENDPOINT}/{bare-domain}; it answers with
# a 302 to the actual image, which requests follows automatically.
_QUIKTURN_ENDPOINT = "https://logos.getquikturn.io"


@st.cache_data(ttl=86400, show_spinner=False)
def ticker_to_domain(ticker: str) -> str | None:
    """Resolve a stock ticker to its bare web domain, e.g. AAPL -> apple.com.

    Uses yfinance's flaky .info["website"], so any hiccup (shape change, rate
    limit, network) returns None and the caller falls back to a monogram.
    """
    try:
        website = yf.Ticker(ticker).info.get("website")
        if not website:
            return None
        netloc = urlparse(website).netloc.removeprefix("www.")
        return netloc or None
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_logo_bytes(ticker: str, asset_type: str = "stock") -> bytes | None:
    """Return PNG bytes for a ticker's logo, or None to signal 'draw a monogram'.

    Crypto reads a bundled local icon (no network). Stocks fetch from quikturn,
    keyed by the resolved company domain. Never raises.
    """
    if asset_type == "crypto":
        icon_path = _ICON_DIR / f"{ticker.lower()}.png"
        try:
            return icon_path.read_bytes() if icon_path.is_file() else None
        except Exception:
            return None

    # --- Stock path. Keyless mode must work: no key -> monogram, no network. ---
    try:
        token = st.secrets.get("QUIKTURN_KEY", "")
    except Exception:
        # No secrets.toml at all (e.g. a fresh clone) — treat as keyless.
        token = ""
    if not token:
        return None

    domain = ticker_to_domain(ticker)
    if not domain:
        return None

    try:
        # Pass the BARE domain only — no protocol, no path — or the API 400s.
        r = requests.get(
            f"{_QUIKTURN_ENDPOINT}/{domain}",
            params={"token": token, "size": 64, "theme": "dark"},
            timeout=3,
        )
        return r.content if r.ok else None
    except requests.RequestException:
        return None


def render_asset_badge(ticker: str, asset_type: str, size: int = 40) -> None:
    """Render a logo image if we have one, else a gradient monogram badge.

    The monogram — a violet->cyan disc with the ticker's first letter — is a
    deliberate design element, so a missing logo looks intentional, never broken.
    """
    logo_bytes = get_logo_bytes(ticker, asset_type)
    if logo_bytes:
        st.image(logo_bytes, width=size)
        return

    letter = html.escape((ticker[:1] or "?").upper())
    font_px = max(11, round(size * 0.44))
    st.markdown(
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f"background:linear-gradient(135deg,#8b7bf7,#4de1d0);color:#0b0a12;"
        f"font-family:Inter,-apple-system,system-ui,sans-serif;font-weight:700;"
        f"font-size:{font_px}px;border:1px solid rgba(255,255,255,0.07);"
        f'display:flex;align-items:center;justify-content:center;">{letter}</div>',
        unsafe_allow_html=True,
    )
