"""nav.py — the icon page-switcher in the sidebar.

A thin wrapper around ``streamlit-option-menu`` so the page navigation lives in
one place and can be restyled without hunting through ``app.py``. The look is
tuned to the Aurora tokens and the owner's reference mockup: an Aurora brand
block on top, muted-lavender labels, a violet icon set, a subtle hover tint,
and a single gold left-border on the active item (gold appears *only* on the
active page — it's the signature accent, used sparingly).

Component constraints worth knowing (they shape what's stylable here):
- ``streamlit-option-menu`` renders inside an **iframe**, so CSS injected via
  ``st.markdown`` in the parent document CANNOT reach the menu. Everything
  visual for the menu itself must go through the ``styles`` dict below, which
  the component applies inside its own frame.
- The component applies ``styles["icon"]`` to *every* icon regardless of state,
  so a differently-colored active icon isn't possible — gold is expressed as
  the active item's left-border + white label instead ("gold only on active").
- The brand block, by contrast, is plain parent-DOM markup, so it's fully
  styleable here (including the Lato face).

Drawer, not router: the menu never replaces the page. "Home" = the portfolio
dashboard (no drawer); any other selection is opened by ``app.py`` as a
slide-out ``st.dialog`` drawer over the dashboard. ``app.py`` owns the
``drawer_page`` state and the drawer's ``on_dismiss`` reset; this module just
renders the menu and returns the selection.

State contract (avoids ``DuplicateWidgetID``):
- The option-menu widget owns the key ``"nav_widget_{nav_epoch}"``. Bumping
  ``nav_epoch`` (done in ``app.py``'s ``_close_drawer``) re-mounts the widget so
  the highlight snaps back to Home after a drawer is dismissed.
- The selection is also mirrored into ``st.session_state["active_page"]`` (a
  separate, non-widget key) for any external reader.
"""
from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

# Page order + matching Bootstrap icon names (streamlit-option-menu ships the
# Bootstrap icon font). Keep these two lists index-aligned.
PAGES: list[str] = ["Home", "Watchlist", "AI Insights", "Providers", "Wallet"]
ICONS: list[str] = ["house", "star", "robot", "plug", "wallet2"]

# Aurora tokens used by the nav (kept local so nav.py has no app.py dependency).
_LABEL = "#c9c6d4"       # default nav-link text (muted lavender)
_ICON = "#8b7bf7"        # violet icon (all states)
_GOLD = "#f5c451"        # active left-border (the signature accent)
_HOVER_BG = "#1a1826"    # subtle hover fill, matches the reference mockup

# streamlit-option-menu style map — applied INSIDE the component's iframe.
# Transparent container so the menu blends into the sidebar (no dark box).
_STYLES = {
    "container": {
        "padding": "0.15rem 0.1rem",
        "background-color": "transparent",
    },
    "icon": {
        "color": _ICON,
        "font-size": "1.05rem",
    },
    "nav-link": {
        "font-family": "'Lato', -apple-system, system-ui, sans-serif",
        "font-size": "0.95rem",
        "font-weight": "700",
        "letter-spacing": "0.01em",
        "color": _LABEL,
        "text-align": "left",
        "margin": "0.18rem 0.1rem",
        "padding": "0.62rem 0.7rem",
        "border-radius": "10px",
        "border-left": "3px solid transparent",  # reserve space so selection never shifts
        "--hover-color": _HOVER_BG,
    },
    # Selected: transparent fill, a 3px gold left-border (rounded by the radius
    # into the reference's "bracket" shape), and white text so the active page
    # reads instantly against the muted rest of the list.
    "nav-link-selected": {
        "background-color": "transparent",
        "border-left": f"3px solid {_GOLD}",
        "border-radius": "10px",
        "color": "#ffffff",
        "font-weight": "700",
    },
}

# Brand block CSS — this markup lives in the parent DOM (not the iframe), so it
# is fully styleable, Lato included. Mirrors the reference mockup's header.
_BRAND_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap');
  .aurora-nav-brand {
    display: flex; align-items: center; gap: 0.62rem;
    padding: 0.35rem 0.4rem 0.9rem 0.5rem;
  }
  .aurora-nav-dot {
    width: 28px; height: 28px; border-radius: 9px; flex-shrink: 0;
    background: radial-gradient(circle at 30% 30%, #4de1d0, #8b7bf7);
    box-shadow: 0 4px 14px rgba(139,123,247,0.35);
  }
  .aurora-nav-name {
    font-family: 'Lato', system-ui, sans-serif;
    font-weight: 900; font-size: 1.05rem; line-height: 1;
    color: #ececf1; letter-spacing: 0.01em;
  }
  .aurora-nav-kicker {
    font-family: 'Lato', system-ui, sans-serif;
    font-size: 0.6rem; font-weight: 700; letter-spacing: 0.2em;
    text-transform: uppercase; color: #6f6b80; margin-top: 0.25rem;
  }
</style>
"""

_BRAND_HTML = (
    '<div class="aurora-nav-brand">'
    '  <div class="aurora-nav-dot"></div>'
    '  <div>'
    '    <div class="aurora-nav-name">Aurora</div>'
    '    <div class="aurora-nav-kicker">Portfolio Lab</div>'
    '  </div>'
    '</div>'
)


def render_nav() -> str:
    """Render the Aurora brand + vertical page nav in the sidebar and return the
    selected page. The menu is a drawer trigger, not a router: "Home" means the
    portfolio dashboard (no drawer); any other value means open that page as a
    slide-out drawer. The menu rests on whatever drawer is currently open (or
    Home), so when ``_close_drawer`` bumps ``nav_epoch`` the widget re-mounts and
    the highlight snaps back to Home.

    The ``nav_epoch`` in the widget key is the reset lever: giving the component
    a new key re-mounts it fresh on ``default_index`` (Home) after a dismiss, so
    a closed drawer never reopens and re-selecting the same item works again."""
    current = st.session_state.get("drawer_page") or "Home"
    if current not in PAGES:
        current = "Home"
    default_index = PAGES.index(current)
    epoch = st.session_state.get("nav_epoch", 0)

    with st.sidebar:
        st.markdown(_BRAND_CSS + _BRAND_HTML, unsafe_allow_html=True)
        selected = option_menu(
            menu_title=None,
            options=PAGES,
            icons=ICONS,
            default_index=default_index,
            orientation="vertical",
            key=f"nav_widget_{epoch}",
            styles=_STYLES,
        )

    # In a live `streamlit run`, the option_menu component ALWAYS returns one of
    # PAGES — even the very first paint returns the default_index item, never
    # None (verified against a real session). So this guard is unreachable in a
    # browser and can never override a real click. It fires ONLY in a
    # frontend-less run — AppTest / bare `import`, where `runtime.exists()` is
    # False and no component reply arrives — recovering to the last-known page
    # so tests and tooling can still drive routing.
    if selected not in PAGES:
        selected = current

    # Kept for any external readers; the drawer state itself lives in
    # st.session_state["drawer_page"], set by the caller from this return value.
    st.session_state["active_page"] = selected
    return selected
