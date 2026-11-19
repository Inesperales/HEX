"""Arcade / retro look for the web app: CSS that .streamlit/config.toml cannot express.

Only presentation lives here. Selectors use the ``data-testid`` attributes of
Streamlit 1.66 (checked against the rendered DOM) and the ``st-key-<key>``
class that Streamlit adds to containers created with ``key=``.
"""

from __future__ import annotations

import streamlit as st

BG = "#140B2E"
PANEL = "#1D1142"
BORDER = "#6B4FD1"
TEXT = "#F3EEFF"
MUTED = "#B9A8F0"
YELLOW = "#FFE14D"
RED = "#FF4D4D"
BLUE = "#4DA3FF"

PIXEL_FONT = "'Press Start 2P', monospace"
TERMINAL_FONT = "'VT323', monospace"

BOARD_PANEL_KEY = "board-panel"
"""``key`` of the container around the board (styled as a panel, max 1000 px)."""

CSS = f"""
<style>
/* ---------- page: background with very subtle scanlines ---------- */
[data-testid="stAppViewContainer"] {{
  background-color: {BG};
  background-image: repeating-linear-gradient(
    0deg, rgba(255,255,255,.03) 0px, rgba(255,255,255,.03) 1px, transparent 1px, transparent 4px);
}}
[data-testid="stHeader"] {{ background: transparent; }}
/* The 22 px base font also enlarges Streamlit's rem-based side padding:
   keep it in pixels so the board can be ~1000 px wide on a laptop. */
[data-testid="stMainBlockContainer"] {{
  padding-left: 32px !important;
  padding-right: 32px !important;
  padding-top: 48px !important;
}}

/* ---------- sidebar: flat panel, thick right border, scrollable ---------- */
[data-testid="stSidebar"] {{
  background-color: {PANEL};
  border-right: 4px solid {BORDER};
}}
[data-testid="stSidebarContent"] {{ overflow-y: auto; }}

/* ---------- title ---------- */
h1 {{
  font-family: {PIXEL_FONT} !important;
  color: {YELLOW} !important;
  text-shadow: 4px 4px 0 {RED};
  letter-spacing: 2px;
}}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
  font-family: {PIXEL_FONT} !important;
  font-size: 14px !important;
  color: {YELLOW};
}}

/* ---------- small pixel labels ---------- */
[data-testid="stWidgetLabel"] p,
[data-testid="stExpander"] summary p,
button p {{
  font-family: {PIXEL_FONT} !important;
  font-size: 12px !important;
  line-height: 1.6 !important;
}}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {MUTED} !important; }}

/* ---------- panels and cards ---------- */
[data-testid="stAlertContainer"],
[data-testid="stExpander"] details,
.st-key-{BOARD_PANEL_KEY} {{
  background-color: {PANEL} !important;
  border: 4px solid {BORDER} !important;
  border-radius: 0 !important;
  box-shadow: 6px 6px 0 #000;
}}
[data-testid="stAlertContainer"] p {{ color: {TEXT} !important; }}

/* ---------- board: as wide as the column, at most 1000 px, centred ---------- */
.st-key-{BOARD_PANEL_KEY} {{
  max-width: 1000px;
  margin: 0 auto 8px auto;
  padding: 0;
}}
.st-key-{BOARD_PANEL_KEY} iframe {{ display: block; }}

/* ---------- buttons ---------- */
button[data-testid="stBaseButton-primary"] {{
  background-color: {YELLOW} !important;
  color: {BG} !important;
  border: 4px solid #000 !important;
  border-radius: 0 !important;
  box-shadow: 4px 4px 0 {RED};
}}
button[data-testid="stBaseButton-primary"] p {{ color: {BG} !important; }}
button[data-testid="stBaseButton-primary"]:hover {{ filter: brightness(1.08); }}
button[data-testid="stBaseButton-primary"]:active {{ transform: translate(2px, 2px); box-shadow: 2px 2px 0 {RED}; }}
button[data-testid="stBaseButton-secondary"] {{
  background-color: transparent !important;
  border: 3px solid {BORDER} !important;
  border-radius: 0 !important;
}}
button[data-testid="stBaseButton-secondary"]:hover:enabled {{ border-color: {YELLOW} !important; }}

/* ---------- inputs: square corners, thick border, yellow accent ---------- */
[data-testid="stSelectbox"] div[role="group"] {{
  border: 3px solid {BORDER} !important;
  border-radius: 0 !important;
}}
[data-testid="stSelectbox"] div[role="group"]:focus-within {{ border-color: {YELLOW} !important; }}
/* Slider thumb: the round div that holds the value label. */
[data-testid="stSlider"] div:has(> [data-testid="stSliderThumbValue"]) {{
  border-radius: 0 !important;
  background-color: {YELLOW} !important;
  box-shadow: 2px 2px 0 #000;
}}
[data-testid="stSliderThumbValue"] p {{ color: {YELLOW} !important; }}
[data-testid="stRadio"] label div:first-child {{ border-radius: 0 !important; }}
</style>
"""


def apply_theme() -> None:
    """Inject the arcade CSS (``st.html`` with only a <style> takes no space)."""
    st.html(CSS)
