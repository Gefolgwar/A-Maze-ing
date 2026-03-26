"""Coordinate math, direction utilities, and debug rendering for mazegen."""

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

DIRECTION_NAMES: Dict[int, str] = {
    NORTH: "N",
    EAST: "E",
    SOUTH: "S",
    WEST: "W",
}

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


def debug_render(hex_grid: List[List[int]]) -> None:
    """Print the maze as a hex grid to the terminal.

    Each cell is displayed as its single hex digit (0-F).
    This is Developer A's debug stub for testing the generator
    logic independently of any UI.

    Args:
        hex_grid: 2-D list of integers (0–15) representing each cell.
    """
    for row in hex_grid:
        print("".join(f"{cell:X}" for cell in row))


def debug_render_walls(hex_grid: List[List[int]]) -> None:
    """Print the maze with box-drawing wall visualization.

    Renders a simple ASCII view where walls are shown as ``+--+``
    and ``|`` characters.  Useful for quick visual inspection.

    Args:
        hex_grid: 2-D list of integers (0–15) representing each cell.
    """
    height: int = len(hex_grid)
    width: int = len(hex_grid[0]) if height > 0 else 0

    for r in range(height):
        # Top walls
        top_line: str = ""
        for c in range(width):
            cell: int = hex_grid[r][c]
            has_north: bool = bool(cell & (1 << NORTH))  # bit=1 → wall
            top_line += "+" + ("--" if has_north else "  ")
        top_line += "+"
        print(top_line)

        # Side walls
        mid_line: str = ""
        for c in range(width):
            cell = hex_grid[r][c]
            has_west: bool = bool(cell & (1 << WEST))
            mid_line += ("|" if has_west else " ") + "  "
        # Right-most wall of last column
        last_cell: int = hex_grid[r][width - 1]
        has_east: bool = bool(last_cell & (1 << EAST))
        mid_line += "|" if has_east else " "
        print(mid_line)

    # Bottom walls of last row
    bottom_line: str = ""
    for c in range(width):
        cell = hex_grid[height - 1][c]
        has_south: bool = bool(cell & (1 << SOUTH))
        bottom_line += "+" + ("--" if has_south else "  ")
    bottom_line += "+"
    print(bottom_line)
