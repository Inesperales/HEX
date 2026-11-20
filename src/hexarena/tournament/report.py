"""Write tournament results as JSON and as a static HTML leaderboard."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from hexarena.tournament.runner import WIN, TournamentResult

REPO_URL = "https://github.com/monianzola/HEX"
WEB_URL = "https://hex-arena-cunef.streamlit.app"
DOCS_URL = "https://hex-arena-cunef.readthedocs.io/es/latest/"

REASON_LABELS = {
    WIN: "conexión",
    "exception": "excepción",
    "timeout": "tiempo agotado",
    "illegal": "jugada ilegal",
    "crash": "proceso caído",
}

_CSS = """
:root {
  --bg: #140B2E; --panel: #1D1142; --panel-2: #2B1B52; --border: #6B4FD1;
  --text: #F3EEFF; --muted: #B9A8F0; --yellow: #FFE14D; --red: #FF4D4D; --blue: #4DA3FF;
  --pixel: "Press Start 2P", monospace; --terminal: "VT323", monospace;
}
* { box-sizing: border-box; }
body {
  margin: 0; color: var(--text); background-color: var(--bg);
  background-image: repeating-linear-gradient(0deg, rgba(255,255,255,.03) 0px,
    rgba(255,255,255,.03) 1px, transparent 1px, transparent 4px);
  font: 22px/1.25 var(--terminal);
}
main { max-width: 980px; margin: 0 auto; padding: 36px 16px 56px; }
a { color: var(--yellow); }
.kicker { margin: 0 0 10px; font: 12px/1.6 var(--pixel); color: var(--muted); letter-spacing: 1px; }
h1 {
  margin: 0 0 14px; font: clamp(26px, 6vw, 44px)/1.2 var(--pixel); color: var(--yellow);
  text-shadow: 4px 4px 0 var(--red); letter-spacing: 2px;
}
h2 { margin: 36px 0 12px; font: 14px/1.5 var(--pixel); color: var(--yellow); }
.meta { color: var(--muted); margin: 0 0 18px; }
.actions { display: flex; flex-wrap: wrap; gap: 14px; margin: 0 0 22px; }
.button {
  display: inline-block; padding: 10px 16px; font: 12px/1.4 var(--pixel); text-decoration: none;
  border: 4px solid #000; background: var(--yellow); color: var(--bg); box-shadow: 4px 4px 0 var(--red);
}
.button.secondary { background: transparent; color: var(--text); border: 3px solid var(--border); box-shadow: none; }
.button:focus-visible { outline: 3px solid var(--text); outline-offset: 3px; }
.card {
  background: var(--panel); border: 4px solid var(--border); box-shadow: 6px 6px 0 #000; overflow-x: auto;
}
table { width: 100%; border-collapse: collapse; }
th, td { padding: 9px 14px; text-align: left; border-bottom: 2px solid var(--panel-2); white-space: nowrap; }
tr:last-child td, tr:last-child th { border-bottom: none; }
thead th { font: 10px/1.6 var(--pixel); color: var(--muted); background: var(--panel-2); }
tbody th { font-weight: normal; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.rank { font: 14px/1.4 var(--pixel); color: var(--muted); }
.first td { background: rgba(255, 225, 77, .07); }
.first .rank { color: var(--yellow); }
.first .rank::after { content: " ★"; }
.bot strong { font-weight: normal; color: var(--text); }
.bot small { display: block; color: var(--muted); font-size: 18px; }
.elo { color: var(--yellow); }
.bar {
  display: inline-block; height: 12px; background: var(--yellow); vertical-align: middle;
  margin-left: 10px; border: 2px solid #000;
}
.matrix td.self { color: var(--border); text-align: center; }
.matrix td.ahead { color: var(--yellow); }
.chips { display: flex; flex-wrap: wrap; gap: 10px; }
.chip { background: var(--panel); border: 3px solid var(--border); padding: 4px 12px; font-size: 20px; }
.empty { padding: 16px; margin: 0; color: var(--muted); }
footer { margin-top: 44px; color: var(--muted); font-size: 20px; }
"""


def to_json(result: TournamentResult) -> str:
    """Serialise ``result`` as pretty-printed JSON."""
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def to_html(result: TournamentResult) -> str:
    """Render a self-contained HTML page with the leaderboard."""
    config = result.config
    names = {e.bot: e.name for e in result.entrants}
    commit = result.commit
    commit_html = (
        f'<a href="{REPO_URL}/commit/{escape(commit)}">{escape(commit[:7])}</a>'
        if commit != "unknown"
        else "desconocido"
    )

    rows = []
    for rank, s in enumerate(result.standings, start=1):
        cls = ' class="first"' if rank == 1 else ""
        author = f"<small>{escape(s.author)}</small>" if s.author else ""
        rows.append(
            f"<tr{cls}><td class=\"rank\">{rank}</td>"
            f'<td class="bot"><strong>{escape(s.name)}</strong>{author}</td>'
            f'<td class="num elo">{s.elo:.0f}</td>'
            f'<td class="num">{s.wins}</td><td class="num">{s.losses}</td>'
            f'<td class="num">{s.win_rate:.0%}<span class="bar" style="width:{s.win_rate * 60:.0f}px"></span></td>'
            f'<td class="num">{s.forfeits}</td></tr>'
        )

    order = [s.bot for s in result.standings]
    matrix_head = "".join(f'<th class="num">{escape(names[b])}</th>' for b in order)
    matrix_rows = []
    for a in order:
        cells = []
        for b in order:
            if a == b:
                cells.append('<td class="self">—</td>')
            else:
                won, lost = result.head_to_head[a][b], result.head_to_head[b][a]
                ahead = ' ahead' if won > lost else ''
                cells.append(f'<td class="num{ahead}">{won}–{lost}</td>')
        matrix_rows.append(f"<tr><th>{escape(names[a])}</th>{''.join(cells)}</tr>")

    incidents = [g for g in result.games if g.reason != WIN]
    if incidents:
        incident_rows = "".join(
            f"<tr><td class=\"num\">{g.index + 1}</td><td>{escape(names[g.loser])}</td>"
            f"<td>{escape(REASON_LABELS.get(g.reason, g.reason))}</td>"
            f"<td>{escape(g.detail[:160])}</td></tr>"
            for g in incidents
        )
        incidents_html = (
            '<div class="card"><table><thead><tr><th class="num">Partida</th><th>Bot</th>'
            f"<th>Motivo</th><th>Detalle</th></tr></thead><tbody>{incident_rows}</tbody></table></div>"
        )
    else:
        incidents_html = '<div class="card"><p class="empty">Ningún bot ha fallado. 🎉</p></div>'

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clasificación hex-arena</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap">
<style>{_CSS}</style>
</head>
<body>
<main>
  <p class="kicker">CLASIFICACIÓN DEL TORNEO</p>
  <h1>HEX ARENA</h1>
  <p class="meta">Actualizada el {escape(result.generated_at)} · commit {commit_html} ·
    {len(result.games)} partidas en {result.duration_seconds:.0f} s</p>
  <nav class="actions">
    <a class="button" href="{WEB_URL}">► JUGAR</a>
    <a class="button secondary" href="{DOCS_URL}tutorial-bot/">SUBE TU BOT</a>
  </nav>

  <div class="chips">
    <span class="chip">Round-robin</span>
    <span class="chip">Tablero {config.board_size}×{config.board_size}</span>
    <span class="chip">{config.games_per_pair} partidas por pareja (mitad con cada color)</span>
    <span class="chip">{config.time_limit:g} s por movimiento</span>
    <span class="chip">Apertura: {config.opening_moves} fichas al azar, jugada con ambos colores</span>
    <span class="chip">Elo inicial {config.initial_elo:g}, K = {config.k_factor:g}, media de {config.elo_orders} órdenes</span>
    <span class="chip">Semilla {config.seed}</span>
  </div>

  <h2>Clasificación</h2>
  <div class="card"><table>
    <thead><tr><th>#</th><th>Bot</th><th class="num">Elo</th><th class="num">Victorias</th>
      <th class="num">Derrotas</th><th class="num">% victorias</th><th class="num">Descalif.</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>

  <h2>Enfrentamientos directos</h2>
  <p class="meta">Cada celda muestra victorias–derrotas del bot de la fila contra el de la columna.</p>
  <div class="card"><table class="matrix">
    <thead><tr><th></th>{matrix_head}</tr></thead>
    <tbody>{''.join(matrix_rows)}</tbody>
  </table></div>

  <h2>Incidencias</h2>
  <p class="meta">Un bot que lanza una excepción, se pasa de tiempo, juega ilegalmente o se cae
    pierde esa partida, y el torneo continúa.</p>
  {incidents_html}

  <footer>Generado automáticamente por <a href="{REPO_URL}">hex-arena</a> ·
    <a href="results.json">resultados en JSON</a> · <a href="{DOCS_URL}torneo/">cómo funciona el torneo</a></footer>
</main>
</body>
</html>
"""


def write_results(result: TournamentResult, output_dir: str | Path) -> tuple[Path, Path]:
    """Write ``results.json`` and ``index.html`` into ``output_dir``.

    Returns:
        The paths of the JSON file and the HTML page.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "results.json"
    html_path = out / "index.html"
    json_path.write_text(to_json(result), encoding="utf-8")
    html_path.write_text(to_html(result), encoding="utf-8")
    return json_path, html_path
