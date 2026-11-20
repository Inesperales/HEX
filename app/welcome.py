"""Welcome window: shown once per session, before anything else happens.

Only presentation: it does not touch the game, the bots or the controls.
While it is open, ``welcome_is_open()`` is ``True`` and the game area does
not start any bot move (see ``game_area`` in app.py).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

SHOWN = "welcome_shown"
"""Session flag: the window has already been shown in this session."""

OPEN = "welcome_open"
"""Session flag: the window is on screen right now."""

CSS_FILE = Path(__file__).resolve().parent / "styles" / "welcome.css"

STEPS_HTML = """
<p class="welcome-title">HEX ARENA</p>
<div class="welcome-steps" role="list">
  <div class="welcome-step" role="listitem"><span class="num red">1</span>
    <span>Por turnos, pon una ficha en un hexágono vacío.</span></div>
  <div class="welcome-step" role="listitem"><span class="num blue">2</span>
    <span>Haz una línea de fichas que una tus dos lados.
      <span class="red-text">Rojo</span>: arriba con abajo.
      <span class="blue-text">Azul</span>: izquierda con derecha.</span></div>
  <div class="welcome-step" role="listitem"><span class="num yellow">3</span>
    <span>Gana quien conecte antes ambos lados. En Hex nunca hay empate.</span></div>
</div>
"""


def welcome_is_open() -> bool:
    """``True`` while the welcome window is on screen."""
    return bool(st.session_state.get(OPEN, False))


def show_welcome_once() -> None:
    """Open the welcome window the first time the page is loaded in this session.

    The "shown" flag is set as soon as the window opens, so it never comes
    back: not after closing it, not when playing, not with "Nueva partida".
    While it is open it is drawn on every run, so a full rerun cannot make it
    vanish and leave the game paused.
    """
    ss = st.session_state
    if ss.get(SHOWN) and not ss.get(OPEN):
        return
    ss[SHOWN] = True
    ss[OPEN] = True
    _welcome_dialog()


def _close() -> None:
    st.session_state[OPEN] = False


@st.dialog("BIENVENIDO A", width="small", dismissible=False)
def _welcome_dialog() -> None:
    st.html(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>")
    st.html(STEPS_HTML)
    if st.button("► JUGAR", key="welcome-play", type="primary", width="stretch", on_click=_close):
        st.rerun()  # Close the window: one full rerun, then the game can move.
    st.html('<p class="welcome-hint">Pulsa Jugar para empezar</p>')
