"""Pattern stamping (42) and structural validation for mazegen."""

from typing import List, Set, Tuple

# 5×3 bitmaps for digits "4" and "2".
# 1 = closed cell (all walls up), 0 = normal maze cell.
_DIGIT_4: List[List[int]] = [
    [1, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1],
]

_DIGIT_2: List[List[int]] = [
    [1, 1, 1],
    [0, 0, 1],
    [1, 1, 1],
    [1, 0, 0],
    [1, 1, 1],
]

# Width / height of each digit bitmap and the gap between them.
_CHAR_H: int = 5
_CHAR_W: int = 3
_GAP: int = 2

# Minimum maze dimensions required to fit the "42" pattern with a 1-cell
# border on every side:  pattern_width = 3 + 2 + 3 = 8, + 2 borders = 10
#                        pattern_height = 5, + 2 borders = 7
_MIN_WIDTH: int = 10
_MIN_HEIGHT: int = 7


def get_42_cells(
    width: int, height: int
) -> Set[Tuple[int, int]]:
    """Return the set of (row, col) cells that form the '42' pattern.

    The pattern is centered in the maze.  Each returned cell should be
    *blocked* (all four walls kept up) so the digits are visible.

    Args:
        width: Number of columns in the maze.
        height: Number of rows in the maze.

    Returns:
        A set of ``(row, col)`` pairs.

    Raises:
        ValueError: If the maze is too small to contain the pattern.
    """
    if width < _MIN_WIDTH or height < _MIN_HEIGHT:
        raise ValueError(
            f"Maze too small for 42 pattern "
            f"(need at least {_MIN_WIDTH}x{_MIN_HEIGHT}, "
            f"got {width}x{height})"
        )

    pattern_w: int = _CHAR_W + _GAP + _CHAR_W  # 8
    pattern_h: int = _CHAR_H                     # 5

    # Top-left corner of the pattern block (centered).
    start_row: int = (height - pattern_h) // 2
    start_col: int = (width - pattern_w) // 2

    cells: Set[Tuple[int, int]] = set()

    # Stamp digit "4".
    for dr in range(_CHAR_H):
        for dc in range(_CHAR_W):
            if _DIGIT_4[dr][dc]:
                cells.add((start_row + dr, start_col + dc))

    # Stamp digit "2" offset by _CHAR_W + _GAP columns.
    offset: int = _CHAR_W + _GAP
    for dr in range(_CHAR_H):
        for dc in range(_CHAR_W):
            if _DIGIT_2[dr][dc]:
                cells.add((start_row + dr, start_col + offset + dc))

    return cells


def stamp_42_on_grid(
    grid: List[List[List[bool]]],
    width: int,
    height: int,
) -> Set[Tuple[int, int]]:
    """Mark cells that form the '42' pattern as fully walled.

    Each cell's wall list is ``[north, south, east, west]`` where
    ``True`` means the wall *exists*.  Pattern cells get all walls set
    to ``True`` so they become impassable blocks that visually spell
    "42".

    Args:
        grid: The mutable wall grid (``grid[row][col]`` → 4-bool list).
        width: Number of columns.
        height: Number of rows.

    Returns:
        The set of ``(row, col)`` cells that were stamped.
    """
    blocked: Set[Tuple[int, int]] = get_42_cells(width, height)
    for r, c in blocked:
        grid[r][c] = [True, True, True, True]  # N, E, S, W — all walls
    return blocked


def validate_no_3x3_open(
    grid: List[List[List[bool]]],
    width: int,
    height: int,
) -> List[Tuple[int, int]]:
    """Find top-left corners of any fully-open 3×3 areas.

    A 3×3 area is "fully open" when every internal wall within the
    3×3 block is absent (``False``).

    Args:
        grid: Wall grid.
        width: Columns.
        height: Rows.

    Returns:
        List of ``(row, col)`` top-left corners where violations exist.
    """
    violations: List[Tuple[int, int]] = []
    for r in range(height - 2):
        for c in range(width - 2):
            if _is_3x3_open(grid, r, c):
                violations.append((r, c))
    return violations


def _is_3x3_open(
    grid: List[List[List[bool]]],
    top: int,
    left: int,
) -> bool:
    """Check whether the 3×3 block starting at (top, left) is fully open."""
    # North=0, East=1, South=2, West=3
    for dr in range(3):
        for dc in range(3):
            walls: List[bool] = grid[top + dr][left + dc]
            # Check south wall for non-bottom rows inside the block.
            if dr < 2 and walls[2]:  # South wall present
                return False
            # Check east wall for non-right cols inside the block.
            if dc < 2 and walls[1]:  # East wall present
                return False
    return True


def fix_3x3_open(
    grid: List[List[List[bool]]],
    width: int,
    height: int,
) -> int:
    """Add walls to break any 3×3 fully-open regions.

    For each violation found, a south wall is added at the center cell
    of the 3×3 block (and the corresponding north wall on the cell below).

    Args:
        grid: Wall grid (mutated in place).
        width: Columns.
        height: Rows.

    Returns:
        Number of violations fixed.
    """
    fixed: int = 0
    while True:
        violations: List[Tuple[int, int]] = validate_no_3x3_open(
            grid, width, height
        )
        if not violations:
            break
        for r, c in violations:
            # Add a south wall at center of block.
            cr: int = r + 1
            cc: int = c + 1
            grid[cr][cc][2] = True   # South
            if cr + 1 < height:
                grid[cr + 1][cc][0] = True  # North of cell below
            fixed += 1
        # Re-check after fixing (new fixes may resolve overlapping blocks).
    return fixed
