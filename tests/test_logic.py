"""Unit tests for the mazegen generator and hex encoding logic."""

from typing import List, Set, Tuple

import pytest

from mazegen import MazeGenerator
from mazegen.patterns import get_42_cells, validate_no_3x3_open


class TestMazeGeneratorCreation:
    """Tests for MazeGenerator instantiation."""

    def test_basic_creation(self) -> None:
        """Generator should initialise with valid dimensions."""
        gen: MazeGenerator = MazeGenerator(10, 10, seed=1)
        assert gen.width == 10
        assert gen.height == 10

    def test_too_small_raises(self) -> None:
        """Width or height < 2 should raise ValueError."""
        with pytest.raises(ValueError, match="must be >= 2"):
            MazeGenerator(1, 5, seed=0)
        with pytest.raises(ValueError, match="must be >= 2"):
            MazeGenerator(5, 1, seed=0)

    def test_deterministic_seed(self) -> None:
        """Same seed should produce identical mazes."""
        g1: MazeGenerator = MazeGenerator(15, 12, seed=99)
        g2: MazeGenerator = MazeGenerator(15, 12, seed=99)
        assert g1.to_hex_format() == g2.to_hex_format()

    def test_different_seeds_differ(self) -> None:
        """Different seeds should (very likely) produce different mazes."""
        g1: MazeGenerator = MazeGenerator(15, 12, seed=1)
        g2: MazeGenerator = MazeGenerator(15, 12, seed=2)
        assert g1.to_hex_format() != g2.to_hex_format()


class TestHexEncoding:
    """Tests for bitwise hex encoding and wall coherency."""

    def test_hex_values_in_range(self) -> None:
        """Every cell value must be in [0, 15]."""
        gen: MazeGenerator = MazeGenerator(20, 15, seed=42)
        for row in gen.to_hex_format():
            for val in row:
                assert 0 <= val <= 15, f"Value {val} out of range"

    def test_grid_dimensions(self) -> None:
        """Hex grid dimensions should match width × height."""
        gen: MazeGenerator = MazeGenerator(20, 15, seed=42)
        grid: List[List[int]] = gen.to_hex_format()
        assert len(grid) == 15
        assert all(len(row) == 20 for row in grid)

    def test_wall_coherency(self) -> None:
        """Neighbouring cells must agree on shared walls.

        This replicates the logic in ``output_validator.py``.
        """
        gen: MazeGenerator = MazeGenerator(20, 15, seed=42)
        g: List[List[int]] = gen.to_hex_format()
        height: int = len(g)
        width: int = len(g[0])
        for r in range(height):
            for c in range(width):
                v: int = g[r][c]
                # North ↔ South of cell above
                if r > 0:
                    assert (v & 1) == ((g[r - 1][c] >> 2) & 1), \
                        f"N/S mismatch at ({c},{r})"
                # East ↔ West of cell to the right
                if c < width - 1:
                    assert ((v >> 1) & 1) == ((g[r][c + 1] >> 3) & 1), \
                        f"E/W mismatch at ({c},{r})"
                # South ↔ North of cell below
                if r < height - 1:
                    assert ((v >> 2) & 1) == (g[r + 1][c] & 1), \
                        f"S/N mismatch at ({c},{r})"
                # West ↔ East of cell to the left
                if c > 0:
                    assert ((v >> 3) & 1) == ((g[r][c - 1] >> 1) & 1), \
                        f"W/E mismatch at ({c},{r})"

    def test_border_walls_present(self) -> None:
        """Outer border of the maze should have walls (bits = 1)."""
        gen: MazeGenerator = MazeGenerator(10, 10, seed=42)
        g: List[List[int]] = gen.to_hex_format()
        for c in range(10):
            assert (g[0][c] & 1) != 0, f"Top border open at col {c}"
            assert (g[9][c] & 4) != 0, f"Bottom border open at col {c}"
        for r in range(10):
            assert (g[r][0] & 8) != 0, f"Left border open at row {r}"
            assert (g[r][9] & 2) != 0, f"Right border open at row {r}"


class TestPattern42:
    """Tests for the '42' pattern embedding."""

    def test_42_present(self) -> None:
        """Blocked cells forming '42' should be all-walls (hex 0)."""
        gen: MazeGenerator = MazeGenerator(20, 15, seed=42)
        blocked: Set[Tuple[int, int]] = gen.blocked_cells
        grid: List[List[int]] = gen.to_hex_format()
        assert len(blocked) > 0, "No 42 pattern found"
        for r, c in blocked:
            assert grid[r][c] == 0xF, f"Blocked cell ({r},{c}) should be 0xF"

    def test_too_small_raises(self) -> None:
        """Maze too small for 42 pattern should raise ValueError."""
        with pytest.raises(ValueError, match="too small"):
            MazeGenerator(5, 5, seed=0)

    def test_42_cell_coordinates(self) -> None:
        """Standalone check that get_42_cells returns valid coords."""
        cells: Set[Tuple[int, int]] = get_42_cells(20, 15)
        for r, c in cells:
            assert 0 <= r < 15 and 0 <= c < 20


class TestNo3x3Open:
    """Tests for 3×3 open area prevention."""

    def test_no_3x3_open(self) -> None:
        """Generated maze should contain no 3×3 fully-open regions."""
        gen: MazeGenerator = MazeGenerator(20, 15, seed=42)
        violations = validate_no_3x3_open(gen.grid, gen.width, gen.height)
        assert violations == [], f"Found 3×3 open areas at {violations}"


class TestPerfectMaze:
    """Tests ensuring a perfect maze has exactly one path."""

    def test_single_path_bfs(self) -> None:
        """BFS from any cell should reach non-blocked cell exactly once."""
        from collections import deque

        gen: MazeGenerator = MazeGenerator(12, 10, seed=7)
        g: List[List[int]] = gen.to_hex_format()
        blocked: Set[Tuple[int, int]] = gen.blocked_cells
        height: int = gen.height
        width: int = gen.width

        # Find start (first non-blocked cell).
        start: Tuple[int, int] = (0, 0)
        for r in range(height):
            for c in range(width):
                if (r, c) not in blocked:
                    start = (r, c)
                    break
            else:
                continue
            break

        visited: Set[Tuple[int, int]] = {start}
        queue = deque([start])
        deltas = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}
        while queue:
            r, c = queue.popleft()
            for bit, (dr, dc) in deltas.items():
                if not (g[r][c] & (1 << bit)):  # bit=0 means open
                    nr, nc = r + dr, c + dc
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append((nr, nc))

        total_open: int = width * height - len(blocked)
        assert len(visited) == total_open, (
            f"BFS reached {len(visited)} cells but expected {total_open}"
        )
