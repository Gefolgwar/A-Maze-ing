"""Core maze generator: Recursive Backtracker, Prim's, hex encoding."""

import random
from typing import List, Optional, Set, Tuple, Generator

from mazegen.patterns import fix_3x3_open, stamp_42_on_grid
from mazegen.utils import (
    DIRECTION_DELTA,
    EAST,
    NORTH,
    OPPOSITE,
    SOUTH,
    WEST,
    Coord,
    neighbors,
)


class MazeGenerator:
    """Generate a 2-D maze encoded as hexadecimal cell values.

    Each cell stores four walls as boolean flags ordered
    ``[North, East, South, West]``.  The hex encoding maps:

    * Bit 0 → North  (``1`` = open / no wall)
    * Bit 1 → East
    * Bit 2 → South
    * Bit 3 → West

    Args:
        width: Number of columns (≥ 2).
        height: Number of rows (≥ 2).
        seed: Integer seed for reproducible generation.
        perfect: When ``True`` the generated maze is *perfect*.
        algorithm: ``"backtracker"`` or ``"prims"``.
        shape: ``"rectangle"`` or ``"diamond"``.

    Raises:
        ValueError: If dimensions < 2, or unknown algorithm/shape.
    """

    def __init__(
        self,
        width: int,
        height: int,
        seed: int,
        perfect: bool = True,
        algorithm: str = "backtracker",
        shape: str = "rectangle",
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError(
                f"Width and height must be >= 2 (got {width}x{height})"
            )
        self.width: int = width
        self.height: int = height
        self.seed: int = seed
        self.perfect: bool = perfect
        if algorithm not in ("backtracker", "prims"):
            raise ValueError(f"Unknown algorithm {algorithm!r}.")
        self.algorithm: str = algorithm
        if shape not in ("rectangle", "diamond"):
            raise ValueError(f"Unknown shape {shape!r}.")
        self.shape: str = shape

        # Cells geometrically outside the chosen shape (rendered blank).
        self._outside: Set[Tuple[int, int]] = set()

        # Wall grid: grid[row][col] = [N_wall, E_wall, S_wall, W_wall]
        # True  = wall present
        # False = wall removed (passage)
        self._grid: List[List[List[bool]]] = [
            [[True, True, True, True] for _ in range(width)]
            for _ in range(height)
        ]

        # Cells blocked by the "42" pattern (impassable).
        self._blocked: Set[Tuple[int, int]] = set()

        # Hex-encoded output cache.
        self._hex_cache: Optional[List[List[int]]] = None

        self._generate()

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate(self) -> None:
        """Run the full generation pipeline."""
        rng: random.Random = random.Random(self.seed)

        # 1. Compute shape mask (cells outside the shape are impassable).
        if self.shape == "diamond":
            self._outside = self._compute_diamond_outside()

        # 2. Stamp the "42" pattern.
        self._blocked = stamp_42_on_grid(
            self._grid, self.width, self.height
        )

        # 3. Carve passages with the selected algorithm.
        if self.algorithm == "prims":
            self._prims_algorithm(rng)
        else:
            self._recursive_backtracker(rng)

        # 4. Ensure no 3×3 fully-open regions exist.
        fix_3x3_open(self._grid, self.width, self.height)

        # 4. Ensure wall coherency (already maintained by _carve).
        self._enforce_wall_coherency()

        # Invalidate hex cache.
        self._hex_cache = None

    def _recursive_backtracker(self, rng: random.Random) -> None:
        """Carve a perfect maze via iterative DFS (Recursive Backtracker).

        Blocked cells (42-pattern) are never visited or carved into.
        """
        visited: Set[Tuple[int, int]] = set(self._blocked) | self._outside

        # Pick a start cell that is not blocked.
        start: Optional[Coord] = self._find_unblocked(0, 0)
        if start is None:
            return  # Entire grid is blocked (degenerate).

        stack: List[Coord] = [start]
        visited.add((start.row, start.col))

        while stack:
            current: Coord = stack[-1]
            unvisited: List[Tuple[int, int, int]] = [
                (d, nr, nc)
                for d, nr, nc in neighbors(
                    current.row, current.col, self.height, self.width
                )
                if (nr, nc) not in visited
            ]

            if not unvisited:
                stack.pop()
                continue

            direction, nr, nc = rng.choice(unvisited)
            self._carve(current.row, current.col, direction)
            visited.add((nr, nc))
            stack.append(Coord(nr, nc))

        # If not perfect, add some extra passages for multiple paths.
        if not self.perfect:
            self._add_extra_passages(
                rng,
                count=max(1, (self.width * self.height) // 20),
            )

    def _prims_algorithm(self, rng: random.Random) -> None:
        """Carve a perfect maze via Randomized Prim's algorithm.

        Maintains a frontier of candidate walls. At each step a random
        wall from the frontier is chosen and, if it connects a visited
        cell to an unvisited (non-blocked) cell, the wall is removed and
        the new cell's own walls are added to the frontier.
        """
        visited: Set[Tuple[int, int]] = set(self._blocked) | self._outside

        start: Optional[Coord] = self._find_unblocked(0, 0)
        if start is None:
            return

        visited.add((start.row, start.col))

        # Frontier: list of (from_row, from_col, direction, to_row, to_col)
        frontier: List[Tuple[int, int, int, int, int]] = []
        for d, (dr, dc) in DIRECTION_DELTA.items():
            nr: int = start.row + dr
            nc: int = start.col + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                frontier.append((start.row, start.col, d, nr, nc))

        while frontier:
            # Swap-and-pop for O(1) random removal.
            idx: int = rng.randrange(len(frontier))
            fr, fc, direction, tr, tc = frontier[idx]
            frontier[idx] = frontier[-1]
            frontier.pop()

            if (tr, tc) in visited:
                continue

            # Carve the passage.
            self._carve(fr, fc, direction)
            visited.add((tr, tc))

            # Expand the frontier from the newly added cell.
            for d, (dr, dc) in DIRECTION_DELTA.items():
                nr = tr + dr
                nc = tc + dc
                if (
                    0 <= nr < self.height
                    and 0 <= nc < self.width
                    and (nr, nc) not in visited
                ):
                    frontier.append((tr, tc, d, nr, nc))

        # If not perfect, add some extra passages.
        if not self.perfect:
            self._add_extra_passages(
                rng,
                count=max(1, (self.width * self.height) // 20),
            )

    def _add_extra_passages(self, rng: random.Random, count: int) -> None:
        """Remove random walls to create alternative paths (imperfect maze)."""
        attempts: int = 0
        added: int = 0
        max_attempts: int = count * 10
        while added < count and attempts < max_attempts:
            attempts += 1
            r: int = rng.randint(0, self.height - 1)
            c: int = rng.randint(0, self.width - 1)
            if (r, c) in self._blocked or (r, c) in self._outside:
                continue
            dirs: List[Tuple[int, int, int]] = [
                (d, nr, nc)
                for d, nr, nc in neighbors(r, c, self.height, self.width)
                if (nr, nc) not in self._blocked
                and (nr, nc) not in self._outside
            ]
            if not dirs:
                continue
            d, nr, nc = rng.choice(dirs)
            if self._grid[r][c][d]:  # Wall still present.
                self._carve(r, c, d)
                added += 1

    def _carve(self, row: int, col: int, direction: int) -> None:
        """Remove the wall between (row, col) and its neighbor in *direction*.

        Also removes the corresponding wall on the neighbor side (coherency).
        """
        dr, dc = DIRECTION_DELTA[direction]
        nr: int = row + dr
        nc: int = col + dc
        self._grid[row][col][direction] = False
        self._grid[nr][nc][OPPOSITE[direction]] = False

    def _find_unblocked(self, start_r: int, start_c: int) -> Optional[Coord]:
        """Find the first non-blocked cell scanning from (start_r, start_c)."""
        for r in range(start_r, self.height):
            c_start: int = start_c if r == start_r else 0
            for c in range(c_start, self.width):
                if (r, c) not in self._blocked and (r, c) not in self._outside:
                    return Coord(r, c)
        return None

    def _compute_diamond_outside(self) -> Set[Tuple[int, int]]:
        """Return cells outside the diamond shape.

        Uses Manhattan distance from the grid centre normalised by the
        half-extents so the diamond fits the full grid.
        """
        half_h: int = self.height // 2
        half_w: int = self.width // 2
        radius: int = min(half_h, half_w)
        cr: int = self.height // 2
        cc: int = self.width // 2
        outside: Set[Tuple[int, int]] = set()
        for r in range(self.height):
            for c in range(self.width):
                if abs(r - cr) + abs(c - cc) > radius:
                    outside.add((r, c))
        return outside

    def _enforce_wall_coherency(self) -> None:
        """Ensure every shared wall agrees between adjacent cells."""
        _all_blocked: Set[Tuple[int, int]] = self._blocked | self._outside
        for r in range(self.height):
            for c in range(self.width):
                if (r, c) in _all_blocked:
                    continue
                # Check south neighbor.
                if r + 1 < self.height and (r + 1, c) not in _all_blocked:
                    s_self: bool = self._grid[r][c][SOUTH]
                    n_neigh: bool = self._grid[r + 1][c][NORTH]
                    if s_self != n_neigh:
                        agreed: bool = s_self and n_neigh
                        self._grid[r][c][SOUTH] = agreed
                        self._grid[r + 1][c][NORTH] = agreed
                # Check east neighbor.
                if c + 1 < self.width and (r, c + 1) not in _all_blocked:
                    e_self: bool = self._grid[r][c][EAST]
                    w_neigh: bool = self._grid[r][c + 1][WEST]
                    if e_self != w_neigh:
                        agreed = e_self and w_neigh
                        self._grid[r][c][EAST] = agreed
                        self._grid[r][c + 1][WEST] = agreed

    # ------------------------------------------------------------------
    # Hex encoding
    # ------------------------------------------------------------------

    def to_hex_format(self) -> List[List[int]]:
        """Encode the maze as a 2-D grid of hex values (0–F).

        Encoding per cell:

        * Bit 0 (1) → North wall closed
        * Bit 1 (2) → East wall closed
        * Bit 2 (4) → South wall closed
        * Bit 3 (8) → West wall closed

        A *wall present* → corresponding bit is **1**.
        A *wall absent*  → corresponding bit is **0**.

        Returns:
            ``height × width`` list of ints in ``[0, 15]``.
        """
        if self._hex_cache is not None:
            return self._hex_cache

        result: List[List[int]] = []
        for r in range(self.height):
            row_vals: List[int] = []
            for c in range(self.width):
                val: int = 0
                walls: List[bool] = self._grid[r][c]
                if walls[NORTH]:
                    val |= 1 << NORTH   # bit 0
                if walls[EAST]:
                    val |= 1 << EAST    # bit 1
                if walls[SOUTH]:
                    val |= 1 << SOUTH   # bit 2
                if walls[WEST]:
                    val |= 1 << WEST    # bit 3
                row_vals.append(val)
            result.append(row_vals)
        self._hex_cache = result
        return result

    def to_hex_string(self) -> str:
        """Return the hex grid as a multi-line string (one char per cell)."""
        grid: List[List[int]] = self.to_hex_format()
        return "\n".join(
            "".join(f"{v:X}" for v in row) for row in grid
        )

    # ------------------------------------------------------------------
    # Step-by-step generation (for animation)
    # ------------------------------------------------------------------

    def iter_generation(self) -> Generator[List[List[int]], None, None]:
        """Yield hex-grid snapshots step-by-step for animated rendering.

        Resets the internal grid, runs setup (shape mask + 42 stamp),
        then yields the grid after every carved passage.  The last yield
        is the fully post-processed maze.

        Usage::

            step_iter = gen.iter_generation()
            first = next(step_iter)          # setup done; read blocked/outside
            for grid in step_iter:           # one snapshot per carved wall
                draw(grid)
        """
        # 1. Reset the grid to all-walls.
        self._grid = [
            [[True, True, True, True] for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self._blocked = set()
        self._outside = set()
        self._hex_cache = None

        rng: random.Random = random.Random(self.seed)

        # 2. Shape mask.
        if self.shape == "diamond":
            self._outside = self._compute_diamond_outside()

        # 3. Stamp 42 pattern.
        self._blocked = stamp_42_on_grid(self._grid, self.width, self.height)

        # 4. Yield initial state (all walls, 42 cells visible).
        self._hex_cache = None
        yield self.to_hex_format()

        # 5. Step-by-step algorithm.
        if self.algorithm == "prims":
            yield from self._prims_steps(rng)
        else:
            yield from self._backtracker_steps(rng)

        # 6. Post-processing.
        fix_3x3_open(self._grid, self.width, self.height)
        self._enforce_wall_coherency()
        self._hex_cache = None
        yield self.to_hex_format()

    def _backtracker_steps(self, rng: random.Random
                           ) -> Generator[List[List[int]], None, None]:
        """Step generator: Recursive Backtracker, one yield per carve."""
        visited: Set[Tuple[int, int]] = set(self._blocked) | self._outside
        start: Optional[Coord] = self._find_unblocked(0, 0)
        if start is None:
            return
        stack: List[Coord] = [start]
        visited.add((start.row, start.col))

        while stack:
            current: Coord = stack[-1]
            unvisited: List[Tuple[int, int, int]] = [
                (d, nr, nc)
                for d, nr, nc in neighbors(
                    current.row, current.col, self.height, self.width
                )
                if (nr, nc) not in visited
            ]
            if not unvisited:
                stack.pop()
                continue
            direction, nr, nc = rng.choice(unvisited)
            self._carve(current.row, current.col, direction)
            visited.add((nr, nc))
            stack.append(Coord(nr, nc))
            self._hex_cache = None
            yield self.to_hex_format()

        if not self.perfect:
            self._add_extra_passages(
                rng, count=max(1, (self.width * self.height) // 20)
            )
            self._hex_cache = None
            yield self.to_hex_format()

    def _prims_steps(self, rng: random.Random
                     ) -> Generator[List[List[int]], None, None]:
        """Step generator: Randomized Prim's, one yield per carve."""
        visited: Set[Tuple[int, int]] = set(self._blocked) | self._outside
        start: Optional[Coord] = self._find_unblocked(0, 0)
        if start is None:
            return
        visited.add((start.row, start.col))

        frontier: List[Tuple[int, int, int, int, int]] = []
        for d, (dr, dc) in DIRECTION_DELTA.items():
            nr: int = start.row + dr
            nc: int = start.col + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                frontier.append((start.row, start.col, d, nr, nc))

        while frontier:
            idx: int = rng.randrange(len(frontier))
            fr, fc, direction, tr, tc = frontier[idx]
            frontier[idx] = frontier[-1]
            frontier.pop()
            if (tr, tc) in visited:
                continue
            self._carve(fr, fc, direction)
            visited.add((tr, tc))
            self._hex_cache = None
            yield self.to_hex_format()
            for d, (dr, dc) in DIRECTION_DELTA.items():
                nr = tr + dr
                nc = tc + dc
                if (
                    0 <= nr < self.height
                    and 0 <= nc < self.width
                    and (nr, nc) not in visited
                ):
                    frontier.append((tr, tc, d, nr, nc))

        if not self.perfect:
            self._add_extra_passages(
                rng, count=max(1, (self.width * self.height) // 20)
            )
            self._hex_cache = None
            yield self.to_hex_format()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def grid(self) -> List[List[List[bool]]]:
        """The internal wall grid (read-only view)."""
        return self._grid

    @property
    def blocked_cells(self) -> Set[Tuple[int, int]]:
        """Cells blocked by the 42 pattern (grey fill)."""
        return set(self._blocked)

    @property
    def outside_cells(self) -> Set[Tuple[int, int]]:
        """Cells outside the chosen shape (rendered blank)."""
        return set(self._outside)
