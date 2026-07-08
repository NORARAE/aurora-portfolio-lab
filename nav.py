"""nav.py — the icon page-switcher in the sidebar.

A thin wrapper around ``streamlit-option-menu`` so the page navigation lives in
one place and can be restyled without hunting through ``app.py``. The look is
tuned to the Aurora tokens: a near-black rail, muted-lavender labels, a violet
icon set, and a single gold left-border on the active item (the only gold in
the nav — it's the app's signature accent, used sparingly).

State contract (important, avoids ``DuplicateWidgetID``):
- The option-menu widget owns the key ``"nav_widget"``.
- The *selected page* is mirrored into ``st.session_state["active_page"]`` —
  a **separate** key. We never bind ``active_page`` as a widget key, so there's
  exactly one widget writing it and no duplicate-ID collision.
"""
from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

# Page order + matching Bootstrap icon names (streamlit-option-menu ships the
# Bootstrap icon font). Keep these two lists index-aligned.
PAGES: list[str] = ["Home", "Watchlist", "AI Insights", "Providers", "Wallet"]
ICONS: list[str] = ["house", "star", "robot", "plug", "wallet2"]

# Aurora tokens used by the nav (kept local so nav.py has no app.py dependency).
_NAV_BG = "#0b0a12"      # near-black rail background
_LABEL = "#c9c6d4"       # default nav-link text (muted lavender)
_ICON = "#8b7bf7"        # violet icon
_HOVER = "#4de1d0"       # teal hover whisper
_GOLD = "#f5c451"        # active left-border (the signature accent)

# streamlit-option-menu style map. Values are plain CSS strings.
_STYLES = {
    "container": {
        "padding": "0.4rem 0.2rem",
        "background-color": _NAV_BG,
        "border-radius": "12px",
    },
    "icon": {
        "color": _ICON,
        "font-size": "1rem",
    },
    "nav-link": {
        "font-family": "'Lato', -apple-system, system-ui, sans-serif",
        "font-size": "0.9rem",
        "font-weight": "600",
        "letter-spacing": "0.02em",
        "color": _LABEL,
        "text-align": "left",
        "margin": "0.15rem 0.1rem",
        "padding": "0.5rem 0.75rem",
        "border-radius": "8px",
        "border-left": "3px solid transparent",  # reserve space so selection doesn't shift
        "--hover-color": "rgba(139,123,247,0.10)",
    },
    # Selected: transparent fill, a 3px gold left-border, and white text so the
    # active page reads instantly against the muted rest of the list.
    "nav-link-selected": {
        "background-color": "transparent",
        "border-left": f"3px solid {_GOLD}",
        "border-radius": "8px",
        "color": "#ffffff",
        "font-weight": "700",
    },
}

# Hover whisper: tint the icon teal on hover. option_menu doesn't expose a
# hover style for the icon directly, so we inject a scoped rule once.
_HOVER_CSS = f"""
<style>
  section[data-testid="stSidebar"] .nav-link:hover {{
    background-color: rgba(139,123,247,0.10) !important;
  }}
  section[data-testid="stSidebar"] .nav-link:hover .icon,
  section[data-testid="stSidebar"] .nav-link:hover i {{
    color: {_HOVER} !important;
  }}
</style>
"""


def render_nav() -> str:
    """Render the vertical page nav in the sidebar and return the active page.

    The returned label is also stored in ``st.session_state["active_page"]`` so
    the rest of the app can branch on it. Selection persists across reruns via
    the widget's own ``key`` — we just read it back out."""
    current = st.session_state.get("active_page", "Home")
    default_index = PAGES.index(current) if current in PAGES else 0

    with st.sidebar:
        # Pull in Lato once (the nav's typeface) alongside the hover rule.
        st.markdown(
            "<style>@import url('https://fonts.googleapis.com/css2?"
            "family=Lato:wght@400;600;700&display=swap');</style>" + _HOVER_CSS,
            unsafe_allow_html=True,
        )
        selected = option_menu(
            menu_title=None,
            options=PAGES,
            icons=ICONS,
            default_index=default_index,
            orientation="vertical",
            key="nav_widget",
            styles=_STYLES,
        )

    # Defensive: on some cold-start / bare-mode renders the component can hand
    # back None before it hydrates. Fall back to the current page so we never
    # route to a phantom selection.
    if selected not in PAGES:
        selected = PAGES[default_index]

    # Mirror into the shared read key (never bound as a widget key → no
    # DuplicateWidgetID). This is the single source of truth callers read.
    st.session_state["active_page"] = selected
    return selected
