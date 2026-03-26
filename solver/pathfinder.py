"""Pathfinding solver using BFS to find the shortest path through a maze."""

from collections import deque
from typing import Deque, Dict, List, Optional, Set, Tuple


# Direction bit positions (must match mazegen encoding).
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

DIRECTION_DELTA: Dict[int, Tuple[int, int]] = {
    NORTH: (-1, 0),
    EAST: (0, 1),
    SOUTH: (1, 0),
    WEST: (0, -1),
}


def solve(
    hex_grid: List[List[int]],
    entry: Tuple[int, int],
    exit_cell: Tuple[int, int],
) -> Optional[str]:
    """Find the shortest path from *entry* to *exit_cell* using BFS.

    The ``hex_grid`` uses the standard bitwise encoding:

    * Bit 0 (``1``) → North wall closed
    * Bit 1 (``2``) → East wall closed
    * Bit 2 (``4``) → South wall closed
    * Bit 3 (``8``) → West wall closed

    Args:
        hex_grid: 2-D list of ints (0–15) encoding cell walls.
        entry: ``(row, col)`` of the maze entry.
        exit_cell: ``(row, col)`` of the maze exit.

    Returns:
        A space-separated string of directions (``"N"``, ``"E"``,
        ``"S"``, ``"W"``) representing the shortest path, or ``None``
        if no path exists.
    """
    height: int = len(hex_grid)
    width: int = len(hex_grid[0]) if height > 0 else 0

    if not (0 <= entry[0] < height and 0 <= entry[1] < width):
        return None
    if not (0 <= exit_cell[0] < height and 0 <= exit_cell[1] < width):
        return None

    # BFS.
    visited: Set[Tuple[int, int]] = {entry}
    # Each queue item: (row, col, path_so_far)
    queue: Deque[Tuple[int, int, List[str]]] = deque()
    queue.append((entry[0], entry[1], []))

    while queue:
        r, c, path = queue.popleft()

        if (r, c) == exit_cell:
            return " ".join(path)

        cell_val: int = hex_grid[r][c]

        for direction, (dr, dc) in DIRECTION_DELTA.items():
            # Check if the direction is open (bit=0 means open).
            if cell_val & (1 << direction):
                continue
            nr: int = r + dr
            nc: int = c + dc
            if 0 <= nr < height and 0 <= nc < width and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, path + [DIRECTION_NAMES[direction]]))

    return None  # No path found.
