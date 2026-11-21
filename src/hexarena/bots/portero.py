"""Portero (bloqueador): corta el camino más corto del rival por donde también me sirve a mí.

1. **Ganar**: si una ficha me hace ganar ya, la pongo.
2. **Bloquear el camino del rival**: miro todas las casillas que están en algún camino más
   corto del rival (las que le faltan para unir sus bordes). De ellas, juego la que está
   más cerca de mi propio camino más corto. Así cada ficha estorba al rival y a la vez me
   acerca a mí.

Usa ``path_slack`` de la librería: para cada casilla vacía dice cuánto más largo sería el
camino de un jugador si tuviera que pasar por ella (0 = está en un camino más corto).
Los empates se deshacen por cercanía al centro. No hay azar.
"""

from __future__ import annotations

import math

from hexarena.bots import Bot, Move, Observation, register_bot
from hexarena.bots.heuristics import WIN_SCORE, center_distance, evaluate, path_slack, with_stone
from hexarena.game.state import opponent


@register_bot("portero")
class Portero(Bot):
    """Gana si puede; si no, se pone en el camino más corto del rival que más le sirve a él."""

    name = "Portero"
    author = "Antonio Orteu, María Sanz, Álvaro Domingo"
    description = "Gana si puede; si no, corta el camino más corto del rival por donde más le sirve a él."

    def __init__(self) -> None:
        self.regla = ""

    def choose_move(self, observation: Observation) -> Move:
        """Elige la jugada que gana o, si no, la que mejor corta al rival.

        Args:
            observation: El tablero, el color que me toca, el tamaño y las jugadas legales.

        Returns:
            La casilla ``(fila, columna)`` donde poner la ficha. Además deja en
            ``self.regla`` qué regla la ha decidido.
        """
        board, me, size = observation.board, observation.player, observation.size
        rival = opponent(me)
        legales = observation.legal_moves
        centro = lambda m: center_distance(m, size)  # noqa: E731

        # 1. Ganar ya.
        for m in sorted(legales, key=centro):
            if evaluate(with_stone(board, m, me), me) == WIN_SCORE:
                self.regla = "1. Ganar"
                return m
        # 2. Cortar el camino más corto del rival por donde más me sirve a mí.
        holgura_rival = path_slack(board, rival)
        holgura_mia = path_slack(board, me)

        def clave(m: Move) -> tuple[float, float, float]:
            """Orden de preferencia: primero las del camino del rival, luego las del mío, luego el centro.

            Args:
                m: Una casilla vacía.

            Returns:
                ``(holgura del rival, holgura mía, distancia al centro)``; gana la menor.
            """
            return (holgura_rival.get(m, math.inf), holgura_mia.get(m, math.inf), centro(m))

        self.regla = "2. Bloquear su camino"
        return min(legales, key=clave)
