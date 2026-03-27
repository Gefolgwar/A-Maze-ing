"""Coordinate math and direction utilities for mazegen."""

from typing import Dict, List, NamedTuple, Tuple


class Coord(NamedTuple):
    """A (row, col) coordinate in the maze grid."""

    row: int
    col: int


# Direction constants — index matches bit position in hex encoding.
# Bit 0 = North, Bit 1 = East, Bit 2 = South, Bit 3 = West.
# A set bit (1) means the wall is closed (present).
NORTH: int = 0
EAST: int = 1
SOUTH: int = 2
WEST: int = 3

# Delta (drow, dcol) for each direction.
DIRECTION_DELTA: Dict[int, Tuple[int, int]] = {
    NORTH: (-1, 0),
    EAST: (0, 1),
    SOUTH: (1, 0),
    WEST: (0, -1),
}

# Opposite direction mapping.
OPPOSITE: Dict[int, int] = {
    NORTH: SOUTH,
    SOUTH: NORTH,
    EAST: WEST,
    WEST: EAST,
}


def in_bounds(row: int, col: int, height: int, width: int) -> bool:
    """Return True if (row, col) is inside the grid."""
    return 0 <= row < height and 0 <= col < width


def neighbors(
    row: int, col: int, height: int, width: int
) -> List[Tuple[int, int, int]]:
    """Return valid neighbor cells as (direction, n_row, n_col) triples."""
    result: List[Tuple[int, int, int]] = []
    for direction, (dr, dc) in DIRECTION_DELTA.items():
        nr: int = row + dr
        nc: int = col + dc
        if in_bounds(nr, nc, height, width):
            result.append((direction, nr, nc))
    return result
