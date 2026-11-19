"""Draw the Hex board as an image and map clicks back to cells.

Geometry (pointy-top hexagons of circumradius ``R``)::

    hex width   w = sqrt(3) * R        (distance between centres in a row)
    row height  h = 1.5 * R            (vertical distance between rows)

    centre of (r, c):
        x = margin + w/2 + c*w + r*w/2     <- each row shifts half a hex right
        y = margin + R   + r*h

With that shift, (r+1, c-1) sits down-left and (r+1, c) down-right of
(r, c), which matches the neighbour rule of :mod:`hexarena.game`.

Style: arcade/neon. Only the stones glow; cells, edges and frame are flat.
Speed: the empty board and one neon stone per colour are drawn once per
board size and cached; drawing a position only stamps the cached stones on
a copy of the cached board, and whole positions are cached too.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from hexarena.game import BLUE, EMPTY, RED, HexState, Move, neighbors

SQRT3 = math.sqrt(3)
SUPERSAMPLE = 2
"""Shapes are drawn at this scale and then reduced, for smooth edges."""

TARGET_WIDTH = 1000
"""Width of the board image in pixels (the app shows it at most this wide)."""

REFERENCE_RADIUS = 50.0
"""Radius at which strokes and glows have their nominal size (they scale with R)."""

# Arcade palette.
BACKGROUND = "#1D1142"  # Panel behind the board.
EMPTY_FILL = "#2B1B52"
CELL_OUTLINE = "#8B6CFF"
RED_EDGE = "#FF4D4D"
BLUE_EDGE = "#4DA3FF"
RED_FILL = "#3A1010"  # Dark body of a red stone.
BLUE_FILL = "#0F2A44"  # Dark body of a blue stone.
NEON = {RED: RED_EDGE, BLUE: BLUE_EDGE}
STONE_FILL = {RED: RED_FILL, BLUE: BLUE_FILL}
HIGHLIGHT = "#FFE14D"  # Last move ring and winning chain.

# Vertex angles of a pointy-top hexagon (y grows downwards):
# top, upper-right, lower-right, bottom, lower-left, upper-left.
_VERTEX_ANGLES = (-90, -30, 30, 90, 150, 210)
TOP, UPPER_RIGHT, LOWER_RIGHT, BOTTOM, LOWER_LEFT, UPPER_LEFT = range(6)

Point = tuple[float, float]


@dataclass(frozen=True)
class BoardGeometry:
    """Pixel geometry of an N×N board (in final, non-supersampled pixels)."""

    size: int
    radius: float

    @property
    def hex_width(self) -> float:
        return SQRT3 * self.radius

    @property
    def row_height(self) -> float:
        return 1.5 * self.radius

    @property
    def margin(self) -> float:
        # Leaves room for the coloured edges and for the glow of edge stones.
        return 0.8 * self.radius

    @property
    def image_size(self) -> tuple[int, int]:
        width = 2 * self.margin + self.hex_width * (1.5 * self.size - 0.5)
        height = 2 * self.margin + 2 * self.radius + self.row_height * (self.size - 1)
        return math.ceil(width), math.ceil(height)

    def scaled(self, nominal: float, low: float, high: float) -> float:
        """A stroke or glow size proportional to the radius, kept within bounds."""
        return min(high, max(low, nominal * self.radius / REFERENCE_RADIUS))

    def center(self, r: int, c: int) -> Point:
        """Pixel centre of cell ``(r, c)``."""
        x = self.margin + self.hex_width / 2 + c * self.hex_width + r * self.hex_width / 2
        y = self.margin + self.radius + r * self.row_height
        return x, y

    def corners(self, r: int, c: int, scale: float = 1.0, shrink: float = 1.0) -> list[Point]:
        """The six vertices of cell ``(r, c)``, multiplied by ``scale``.

        ``shrink`` < 1 returns a smaller concentric hexagon.
        """
        cx, cy = self.center(r, c)
        return _hexagon(cx * scale, cy * scale, self.radius * shrink * scale)


def _hexagon(cx: float, cy: float, radius: float) -> list[Point]:
    return [
        (cx + radius * math.cos(math.radians(a)), cy + radius * math.sin(math.radians(a)))
        for a in _VERTEX_ANGLES
    ]


@lru_cache(maxsize=None)
def geometry(size: int) -> BoardGeometry:
    """Geometry for an N×N board, scaled so the image is ``TARGET_WIDTH`` wide."""
    if size < 1:
        raise ValueError(f"Board size must be positive, got {size}")
    radius = TARGET_WIDTH / (SQRT3 * (1.5 * size - 0.5) + 1.6)
    return BoardGeometry(size=size, radius=radius)


def pixel_to_cell(x: float, y: float, size: int) -> tuple[int, int] | None:
    """Return the cell under pixel ``(x, y)``, or ``None`` if it is off the board.

    Picks the cell whose centre is nearest. Because hexagons tile the plane,
    the nearest centre is exactly the hexagon that contains the point. Clicks
    farther than one radius from every centre (margins, outside the
    rhombus) are discarded.
    """
    geo = geometry(size)
    best: tuple[int, int] | None = None
    best_dist = math.inf
    for r in range(size):
        for c in range(size):
            cx, cy = geo.center(r, c)
            dist = math.hypot(x - cx, y - cy)
            if dist < best_dist:
                best, best_dist = (r, c), dist
    return best if best_dist <= geo.radius else None


def winning_chain(state: HexState) -> set[Move]:
    """Stones of the winner that belong to a group touching both of its edges.

    Returns an empty set if there is no winner or the win was not by
    connection (for example, the opponent forfeited).
    """
    player = state.winner
    if player is None:
        return set()
    size = state.size
    board = state.board
    seen: set[Move] = set()
    chain: set[Move] = set()
    for r in range(size):
        for c in range(size):
            if board[r][c] != player or (r, c) in seen:
                continue
            group = {(r, c)}
            queue = deque([(r, c)])
            while queue:
                cell = queue.popleft()
                for nr, nc in neighbors(cell, size):
                    if board[nr][nc] == player and (nr, nc) not in group:
                        group.add((nr, nc))
                        queue.append((nr, nc))
            seen |= group
            axis = 0 if player == RED else 1
            coords = {cell[axis] for cell in group}
            if 0 in coords and size - 1 in coords:
                chain |= group
    return chain


def _border_lines(geo: BoardGeometry, scale: float) -> dict[str, list[list[Point]]]:
    """Polylines that follow the outer outline of the edge hexagons."""
    n = geo.size

    def v(r: int, c: int, k: int) -> Point:
        return geo.corners(r, c, scale)[k]

    top = [v(0, 0, UPPER_LEFT)]
    for c in range(n):
        top += [v(0, c, TOP), v(0, c, UPPER_RIGHT)]
    bottom = [v(n - 1, 0, LOWER_LEFT)]
    for c in range(n):
        bottom += [v(n - 1, c, BOTTOM), v(n - 1, c, LOWER_RIGHT)]
    left: list[Point] = []
    for r in range(n):
        left += [v(r, 0, UPPER_LEFT), v(r, 0, LOWER_LEFT)]
    right: list[Point] = []
    for r in range(n):
        right += [v(r, n - 1, UPPER_RIGHT), v(r, n - 1, LOWER_RIGHT)]
    return {RED_EDGE: [top, bottom], BLUE_EDGE: [left, right]}


# --------------------------------------------------------------------------- cached layers


@lru_cache(maxsize=None)
def _empty_board(size: int) -> Image.Image:
    """The board with no stones: flat cells, flat coloured edges. RGBA, final size."""
    geo = geometry(size)
    s = SUPERSAMPLE
    width, height = geo.image_size
    image = Image.new("RGBA", (width * s, height * s), BACKGROUND)
    draw = ImageDraw.Draw(image)

    # Coloured edges, drawn first: the cells cover their inner half, so the
    # visible part is half the line width (about 8 px).
    visible_edge = geo.scaled(8, 6, 10)
    for color, lines in _border_lines(geo, s).items():
        for line in lines:
            draw.line(line, fill=color, width=round(2 * visible_edge * s), joint="curve")

    outline = round(geo.scaled(3, 2, 4) * s)
    for r in range(size):
        for c in range(size):
            draw.polygon(geo.corners(r, c, s), fill=EMPTY_FILL, outline=CELL_OUTLINE, width=outline)
    return image.reduce(s)


def _sprite_size(geo: BoardGeometry) -> int:
    """Side of a stone sprite: the hexagon plus room for its outer glow."""
    pad = 3 * geo.scaled(8, 5, 12) + 2
    return math.ceil(2 * (geo.radius + pad))


@lru_cache(maxsize=None)
def _stone_sprite(size: int, player: int) -> Image.Image:
    """One neon stone (RGBA), centred in its sprite, glow included.

    CSS equivalent: dark background, 3 px border of the player's colour and
    ``box-shadow: 0 0 16px color, inset 0 0 12px color``.
    """
    geo = geometry(size)
    s = SUPERSAMPLE
    side = _sprite_size(geo) * s
    centre = side / 2
    radius = geo.radius * s
    color = NEON[player]

    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).polygon(_hexagon(centre, centre, radius), fill=255)

    # Outer glow: the hexagon in the neon colour, blurred.
    outer_alpha = mask.filter(ImageFilter.GaussianBlur(geo.scaled(8, 5, 12) * s))
    sprite = Image.new("RGBA", (side, side), color)
    sprite.putalpha(outer_alpha)

    # Dark body.
    body = Image.new("RGBA", (side, side), STONE_FILL[player])
    body.putalpha(mask)
    sprite.alpha_composite(body)

    # Inner glow: colour that fades from the edge towards the centre.
    edge_glow = ImageChops.invert(mask).filter(ImageFilter.GaussianBlur(geo.scaled(6, 4, 9) * s))
    inner_alpha = ImageChops.multiply(edge_glow, mask)
    inner = Image.new("RGBA", (side, side), color)
    inner.putalpha(inner_alpha)
    sprite.alpha_composite(inner)

    # Crisp border, inside the hexagon.
    border = geo.scaled(3, 2.5, 4.5) * s
    ImageDraw.Draw(sprite).polygon(
        _hexagon(centre, centre, radius - border / 2), outline=color, width=round(border)
    )
    return sprite.reduce(s)


@lru_cache(maxsize=None)
def _ring_sprite(size: int, kind: str) -> Image.Image:
    """Yellow marks drawn inside a stone: ``"last"`` (ring) or ``"win"`` (inner hexagon)."""
    geo = geometry(size)
    s = SUPERSAMPLE
    side = _sprite_size(geo) * s
    centre = side / 2
    width = round(geo.scaled(3, 2, 4.5) * s)
    sprite = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    if kind == "last":
        ring = geo.radius * 0.42 * s
        draw.ellipse([centre - ring, centre - ring, centre + ring, centre + ring], outline=HIGHLIGHT, width=width)
    else:
        draw.polygon(_hexagon(centre, centre, geo.radius * 0.72 * s), outline=HIGHLIGHT, width=width)
    return sprite.reduce(s)


def _stamp(image: Image.Image, sprite: Image.Image, geo: BoardGeometry, cell: Move) -> None:
    cx, cy = geo.center(*cell)
    half = sprite.width / 2
    image.alpha_composite(sprite, dest=(round(cx - half), round(cy - half)))


# --------------------------------------------------------------------------- public API


def draw_board(state: HexState, last_move: Move | None = None, size: int | None = None) -> Image.Image:
    """Render ``state`` as an RGB image.

    Args:
        state: Position to draw.
        last_move: Cell to mark with a yellow ring (the most recent move).
        size: Board side N. Defaults to ``state.size``; if given it must match.

    Returns:
        A PIL image of size ``geometry(size).image_size``.
    """
    size = state.size if size is None else size
    if size != state.size:
        raise ValueError(f"size={size} does not match the {state.size}x{state.size} state")
    return _draw_cached(state, last_move, size).copy()


def draw_board_for_web(state: HexState, last_move: Move | None = None, size: int | None = None) -> Image.Image:
    """Same picture as :func:`draw_board`, reduced to a 256-colour palette.

    A palette PNG of the neon board is about 4 times smaller than an RGB one
    (the glows are gradients) and much faster to encode, so the web app sends
    this version. The result is cached: do not modify it.
    """
    size = state.size if size is None else size
    if size != state.size:
        raise ValueError(f"size={size} does not match the {state.size}x{state.size} state")
    return _palette_cached(state, last_move, size)


@lru_cache(maxsize=64)
def _palette_cached(state: HexState, last_move: Move | None, size: int) -> Image.Image:
    return _draw_cached(state, last_move, size).quantize(256, method=Image.Quantize.FASTOCTREE)


@lru_cache(maxsize=64)
def _draw_cached(state: HexState, last_move: Move | None, size: int) -> Image.Image:
    geo = geometry(size)
    image = _empty_board(size).copy()
    for r, row in enumerate(state.board):
        for c, value in enumerate(row):
            if value != EMPTY:
                _stamp(image, _stone_sprite(size, value), geo, (r, c))
    for cell in winning_chain(state):
        _stamp(image, _ring_sprite(size, "win"), geo, cell)
    if last_move is not None:
        _stamp(image, _ring_sprite(size, "last"), geo, last_move)
    return image.convert("RGB")
