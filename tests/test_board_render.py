"""Tests for app/board_render.py: pixel <-> cell geometry and board drawing."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

pytest.importorskip("PIL")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from board_render import (  # noqa: E402
    BLUE_EDGE,
    BLUE_FILL,
    EMPTY_FILL,
    HIGHLIGHT,
    RED_EDGE,
    RED_FILL,
    TARGET_WIDTH,
    draw_board,
    draw_board_for_web,
    geometry,
    pixel_to_cell,
    winning_chain,
)

from hexarena.game import BLUE, RED, HexGame, HexState, neighbors  # noqa: E402

SIZES = [1, 5, 7, 11]


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def close(a: tuple[int, ...], b: tuple[int, ...], tol: int = 12) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a, b))


# --------------------------------------------------------------------------- geometry


@pytest.mark.parametrize("size", SIZES)
def test_center_of_each_cell_maps_to_that_cell(size: int) -> None:
    geo = geometry(size)
    for r in range(size):
        for c in range(size):
            x, y = geo.center(r, c)
            assert pixel_to_cell(x, y, size) == (r, c)


@pytest.mark.parametrize("size", SIZES)
def test_points_inside_a_hexagon_map_to_it(size: int) -> None:
    geo = geometry(size)
    inradius = geo.hex_width / 2
    for r in range(size):
        for c in range(size):
            cx, cy = geo.center(r, c)
            for angle in range(0, 360, 30):
                x = cx + 0.9 * inradius * math.cos(math.radians(angle))
                y = cy + 0.9 * inradius * math.sin(math.radians(angle))
                assert pixel_to_cell(x, y, size) == (r, c)


@pytest.mark.parametrize("size", SIZES)
def test_points_outside_the_board_return_none(size: int) -> None:
    width, height = geometry(size).image_size
    for x, y in [(-50, -50), (1, 1), (width - 1, 1), (1, height - 1), (width + 100, height / 2), (width / 2, -40)]:
        assert pixel_to_cell(x, y, size) is None


def test_neighbor_centers_match_game_neighbors() -> None:
    """Centres at one hex-width distance are exactly the game's neighbours."""
    size = 7
    geo = geometry(size)
    for r in range(size):
        for c in range(size):
            x, y = geo.center(r, c)
            close_cells = {
                (rr, cc)
                for rr in range(size)
                for cc in range(size)
                if (rr, cc) != (r, c) and math.dist((x, y), geo.center(rr, cc)) < geo.hex_width * 1.01
            }
            assert close_cells == set(neighbors((r, c), size))


def test_board_is_about_target_width_for_every_size() -> None:
    """Every board size 5-11 is drawn ~1000 px wide (it scales, it does not shrink)."""
    for size in range(5, 12):
        width, height = geometry(size).image_size
        assert TARGET_WIDTH - 2 <= width <= TARGET_WIDTH + 2
        assert 550 <= height <= 750


# --------------------------------------------------------------------------- drawing


@pytest.mark.parametrize("size", SIZES)
def test_draw_board_returns_image_of_expected_size(size: int) -> None:
    state = HexGame(size).initial_state()
    image = draw_board(state, None, size)
    assert image.size == geometry(size).image_size
    assert image.mode == "RGB"


def test_draw_board_colours_cells() -> None:
    game = HexGame(5)
    state = game.play(game.play(game.initial_state(), (2, 2)), (0, 0))
    image = draw_board(state, None, 5)
    geo = geometry(5)

    def pixel(r: int, c: int) -> tuple[int, int, int]:
        x, y = geo.center(r, c)
        return image.getpixel((round(x), round(y)))  # type: ignore[return-value]

    assert close(pixel(2, 2), hex_to_rgb(RED_FILL))
    assert close(pixel(0, 0), hex_to_rgb(BLUE_FILL))
    assert close(pixel(4, 4), hex_to_rgb(EMPTY_FILL))


@pytest.mark.parametrize(("player", "edge"), [(RED, RED_EDGE), (BLUE, BLUE_EDGE)])
@pytest.mark.parametrize("size", [5, 11])
def test_stones_have_a_neon_border_and_glow(size: int, player: int, edge: str) -> None:
    game = HexGame(size)
    state = game.initial_state()
    if player == BLUE:
        state = game.play(state, (0, 0))
    state = game.play(state, (size // 2, size // 2))
    image = draw_board(state, None, size)
    geo = geometry(size)
    x, y = geo.center(size // 2, size // 2)
    border = image.getpixel((round(x), round(y - geo.radius + 2)))  # Just inside the top vertex.
    assert close(border, hex_to_rgb(edge), tol=60)
    # The glow tints the empty cell next to the stone towards the neon colour.
    nx, ny = geo.center(size // 2, size // 2 + 1)
    glow = image.getpixel((round(nx - geo.hex_width * 0.38), round(ny)))
    plain = draw_board(HexGame(size).initial_state(), None, size).getpixel((round(nx - geo.hex_width * 0.38), round(ny)))
    channel = 0 if player == RED else 2
    assert glow[channel] > plain[channel] + 8


def test_last_move_is_marked_with_a_yellow_ring() -> None:
    game = HexGame(5)
    state = game.play(game.initial_state(), (2, 2))
    geo = geometry(5)
    x, y = geo.center(2, 2)
    ring = (round(x + geo.radius * 0.42 - 2), round(y))  # PIL draws the outline inwards.
    with_marker = draw_board(state, (2, 2), 5)
    without = draw_board(state, None, 5)
    assert close(with_marker.getpixel(ring), hex_to_rgb(HIGHLIGHT), tol=60)
    assert close(without.getpixel(ring), hex_to_rgb(RED_FILL), tol=25)
    # The centre of the stone stays dark: it is a ring, not a dot.
    assert close(with_marker.getpixel((round(x), round(y))), hex_to_rgb(RED_FILL))


def test_web_version_is_a_small_palette_image_of_the_same_board() -> None:
    import io

    game = HexGame(7)
    state = game.play(game.play(game.initial_state(), (3, 3)), (2, 4))
    rgb = draw_board(state, (2, 4), 7)
    web = draw_board_for_web(state, (2, 4), 7)
    assert web.mode == "P" and web.size == rgb.size
    rgb_png, web_png = io.BytesIO(), io.BytesIO()
    rgb.save(rgb_png, format="PNG", compress_level=6)
    web.save(web_png, format="PNG", compress_level=6)
    assert len(web_png.getvalue()) < len(rgb_png.getvalue()) / 2
    x, y = geometry(7).center(3, 3)
    assert close(web.convert("RGB").getpixel((round(x), round(y))), hex_to_rgb(RED_FILL), tol=20)


def test_cached_drawings_are_not_shared_with_callers() -> None:
    """draw_board returns a copy: changing it must not change later drawings."""
    state = HexGame(5).initial_state()
    first = draw_board(state, None, 5)
    first.paste((255, 0, 255), (0, 0, first.width, first.height))
    second = draw_board(state, None, 5)
    assert second.getpixel((first.width // 2, first.height // 2)) != (255, 0, 255)


def test_each_position_gets_its_own_drawing() -> None:
    game = HexGame(5)
    a = game.play(game.initial_state(), (0, 0))
    b = game.play(game.initial_state(), (4, 4))
    assert draw_board(a, None, 5).tobytes() != draw_board(b, None, 5).tobytes()


def test_draw_board_rejects_mismatched_size() -> None:
    with pytest.raises(ValueError):
        draw_board(HexGame(5).initial_state(), None, 7)


# --------------------------------------------------------------------------- winning chain


def test_winning_chain_for_red_column() -> None:
    game = HexGame(3)
    state = game.initial_state()
    for move in [(0, 1), (0, 0), (1, 1), (2, 2), (2, 1)]:
        state = game.play(state, move)
    assert state.winner == RED
    assert winning_chain(state) == {(0, 1), (1, 1), (2, 1)}


def test_winning_chain_for_blue_row() -> None:
    game = HexGame(3)
    state = game.initial_state()
    for move in [(0, 0), (1, 0), (0, 1), (1, 1), (2, 2), (1, 2)]:
        state = game.play(state, move)
    assert state.winner == BLUE
    assert winning_chain(state) == {(1, 0), (1, 1), (1, 2)}


def test_no_chain_without_winner_or_on_forfeit() -> None:
    state = HexGame(3).initial_state()
    assert winning_chain(state) == set()
    forfeit = HexState(board=state.board, to_move=BLUE, winner=RED)
    assert winning_chain(forfeit) == set()
