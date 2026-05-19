"""
2D grid math primitives.

D&D 5e Player's Handbook uses 5ft per square. Diagonal movement: simple
rule (PHB) is 5ft per diagonal. Variant rule (DMG): alternates 5/10/5/10.
We use the simple rule — Chebyshev distance — to match how "Arcane Quest"
and most digital VTTs behave. Family game, fast turns.
"""
from __future__ import annotations

from storyforge.core.models import Cell, Coord, Room, TerrainKind


FEET_PER_CELL = 5


# ─────────────────────── Cell accessors ───────────────────────

def cell_index(room: Room, coord: Coord) -> int:
    """Convert (x, y) into the row-major index for room.cells."""
    return coord.y * room.width + coord.x


def get_cell(room: Room, coord: Coord) -> Cell:
    """Fetch the Cell at coord. Raises IndexError if out of bounds."""
    if not in_bounds(room, coord):
        raise IndexError(f"Coord {coord} out of bounds for room {room.id}")
    return room.cells[cell_index(room, coord)]


def set_cell(room: Room, coord: Coord, cell: Cell) -> None:
    """In-place cell replacement. Caller responsible for state.commit()."""
    room.cells[cell_index(room, coord)] = cell


def in_bounds(room: Room, coord: Coord) -> bool:
    return 0 <= coord.x < room.width and 0 <= coord.y < room.height


# ─────────────────────── Distance + traversal ───────────────────────

def chebyshev_distance(a: Coord, b: Coord) -> int:
    """
    Number of grid cells between two coords using the simple 5e rule
    (diagonal counts as one square). Multiply by FEET_PER_CELL for feet.
    """
    return max(abs(a.x - b.x), abs(a.y - b.y))


def feet_between(a: Coord, b: Coord) -> int:
    return chebyshev_distance(a, b) * FEET_PER_CELL


def is_traversable(cell: Cell) -> bool:
    """A cell a character can stand in (or pass through)."""
    if cell.terrain in (TerrainKind.WALL,):
        return False
    if cell.occupant_id is not None:
        return False
    return True


def movement_cost_feet(cell: Cell) -> int:
    """How many feet a single cell costs to enter."""
    if cell.terrain == TerrainKind.DIFFICULT:
        return FEET_PER_CELL * 2
    return FEET_PER_CELL


# ─────────────────────── Pathfinding (MVP: line check) ───────────────────────

def line_coords(a: Coord, b: Coord) -> list[Coord]:
    """
    Bresenham-ish line from a to b inclusive. Used for line-of-sight
    and simple "can I walk straight there?" checks in MVP.
    """
    x0, y0, x1, y1 = a.x, a.y, b.x, b.y
    coords: list[Coord] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        coords.append(Coord(x=x0, y=y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return coords


def path_is_clear(room: Room, start: Coord, end: Coord) -> bool:
    """
    True if a straight line from start to end traverses only traversable
    cells (excluding the start, including the end). MVP-grade — replace
    with A* when v0.2 introduces obstacle-rich rooms.
    """
    line = line_coords(start, end)[1:]  # exclude start (self)
    return all(is_traversable(get_cell(room, c)) for c in line)
