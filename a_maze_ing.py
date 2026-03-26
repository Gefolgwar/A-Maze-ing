#!/usr/bin/env python3
"""A-Maze-Ing — maze generation, solving, and visualization.

Entry point that reads ``config.txt``, generates a maze, solves it,
writes the output file, and optionally launches a UI.

Usage::

    python a_maze_ing.py config.txt
"""

import configparser
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

from mazegen import MazeGenerator
from solver.pathfinder import solve as solve_maze
from ui.terminal import TerminalUI

# ---------------------------------------------------------------------------
# MockGenerator (Developer B stub — used when the real generator is absent)
# ---------------------------------------------------------------------------


class MockGenerator:
    """Hardcoded 5×5 maze for UI/solver development without the real generator.

    The mock returns a pre-built hex grid so the CLI, solver, and UI
    can be developed and tested independently of the core algorithm.
    """

    def __init__(self) -> None:
        self.width: int = 5
        self.height: int = 5
        # A simple 5×5 perfect maze encoded in hex.
        self._hex_grid: List[List[int]] = [
            [0x9, 0x3, 0x5, 0x5, 0x7],
            [0xA, 0x9, 0x6, 0xC, 0x3],
            [0xA, 0xC, 0x3, 0xD, 0x2],
            [0xA, 0xD, 0x2, 0xC, 0x2],
            [0xC, 0x5, 0x6, 0xD, 0x6],
        ]

    def to_hex_format(self) -> List[List[int]]:
        """Return the hardcoded hex grid."""
        return self._hex_grid

    def to_hex_string(self) -> str:
        """Return the hex grid as a string."""
        return "\n".join(
            "".join(f"{v:X}" for v in row) for row in self._hex_grid
        )


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def parse_config(path: str) -> Dict[str, str]:
    """Parse a ``KEY=VALUE`` config file.

    Args:
        path: Path to the config file (e.g. ``config.txt``).

    Returns:
        Dictionary of string keys and values.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If a required key is missing.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    config: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line: str = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(
                    f"Malformed line {lineno} in {path}: {line!r}"
                )
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()

    required_keys: List[str] = [
        "WIDTH", "HEIGHT", "SEED", "PERFECT", "ENTRY", "EXIT", "OUTPUT_FILE",
    ]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    return config


def parse_settings(path: str) -> Dict[str, str]:
    """Parse a ``settings.ini`` file for UI colours/themes.

    Args:
        path: Path to the INI file.

    Returns:
        Flat dictionary of settings (section headers are ignored).
    """
    settings: Dict[str, str] = {}
    if not os.path.isfile(path):
        return settings

    parser: configparser.ConfigParser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    for section in parser.sections():
        for key, value in parser.items(section):
            # configparser lowercases keys — restore PascalCase by convention.
            settings[key] = value
    return settings


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------


def _parse_coord(text: str) -> Tuple[int, int]:
    """Parse ``'col,row'`` into ``(row, col)``."""
    parts: List[str] = text.split(",")
    if len(parts) != 2:
        raise ValueError(f"Invalid coordinate: {text!r} (expected col,row)")
    col: int = int(parts[0].strip())
    row: int = int(parts[1].strip())
    return (row, col)


# ---------------------------------------------------------------------------
# Output file
# ---------------------------------------------------------------------------


def write_output(
    path: str,
    hex_grid: List[List[int]],
    entry: Tuple[int, int],
    exit_cell: Tuple[int, int],
    solution: Optional[str],
) -> None:
    """Write the maze output file.

    Format::

        <hex rows>
        <empty line>
        Entry: col,row
        Exit:  col,row
        Solution: N E S W …

    Args:
        path: Destination file path.
        hex_grid: 2-D hex-encoded grid.
        entry: ``(row, col)`` entry.
        exit_cell: ``(row, col)`` exit.
        solution: Space-separated direction string, or ``None``.
    """
    with open(path, "w", encoding="utf-8") as fh:
        for row in hex_grid:
            fh.write("".join(f"{v:X}" for v in row) + "\n")
        fh.write("\n")
        fh.write(f"Entry: {entry[1]},{entry[0]}\n")
        fh.write(f"Exit: {exit_cell[1]},{exit_cell[0]}\n")
        fh.write(f"Solution: {solution if solution else 'NO PATH'}\n")


# ---------------------------------------------------------------------------
# Solution path reconstruction
# ---------------------------------------------------------------------------


_DIR_DELTA: Dict[str, Tuple[int, int]] = {
    "N": (-1, 0),
    "E": (0, 1),
    "S": (1, 0),
    "W": (0, -1),
}


def _solution_to_cells(
    entry: Tuple[int, int], solution: str
) -> List[Tuple[int, int]]:
    """Convert a direction string into a list of ``(row, col)`` cells."""
    cells: List[Tuple[int, int]] = [entry]
    r, c = entry
    for d in solution.split():
        dr, dc = _DIR_DELTA[d]
        r += dr
        c += dc
        cells.append((r, c))
    return cells


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Application entry point."""
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <config.txt>", file=sys.stderr)
        sys.exit(1)

    config_path: str = sys.argv[1]

    try:
        config: Dict[str, str] = parse_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error reading config: {exc}", file=sys.stderr)
        sys.exit(1)

    width: int = int(config["WIDTH"])
    height: int = int(config["HEIGHT"])
    perfect: bool = config["PERFECT"].strip().lower() in ("true", "1", "yes")
    entry: Tuple[int, int] = _parse_coord(config["ENTRY"])
    exit_cell: Tuple[int, int] = _parse_coord(config["EXIT"])
    output_path: str = config["OUTPUT_FILE"]

    # Mutable seed — incremented on each re-generation.
    _seed: List[int] = [int(config["SEED"])]
    # Mutable algorithm — toggled on "Change algorithm" action.
    _algo: List[str] = ["backtracker"]
    _ALGO_LABELS: Dict[str, str] = {
        "backtracker": "Recursive Backtracker",
        "prims": "Prim's",
    }
    # Mutable shape — toggled on "Change shape" action.
    _shape: List[str] = ["rectangle"]
    _SHAPE_LABELS: Dict[str, str] = {
        "rectangle": "Rectangle",
        "diamond": "Diamond",
    }
    # Original entry/exit from config (used to restore when switching back).
    _orig_entry: Tuple[int, int] = entry
    _orig_exit: Tuple[int, int] = exit_cell
    # Mutable effective entry/exit (may change for diamond).
    _entry: List[Tuple[int, int]] = [entry]
    _exit: List[Tuple[int, int]] = [exit_cell]

    # --- Load UI settings ---------------------------------------------------
    settings_path: str = os.path.join(
        os.path.dirname(os.path.abspath(config_path)), "settings.ini"
    )
    settings: Dict[str, str] = {}
    try:
        settings = parse_settings(settings_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not load settings.ini: {exc}", file=sys.stderr)

    # --- Helper: generate + solve -------------------------------------------
    def _generate_and_solve(seed: int) -> Optional[
        Tuple[
            List[List[int]],
            Optional[List[Tuple[int, int]]],
            Set[Tuple[int, int]],
            Set[Tuple[int, int]],
        ]
    ]:
        """Run the generator and solver; return (grid, sol, blocked, outside)."""
        eff_entry: Tuple[int, int] = _entry[0]
        eff_exit: Tuple[int, int] = _exit[0]
        try:
            gen: MazeGenerator = MazeGenerator(
                width=width, height=height, seed=seed,
                perfect=perfect, algorithm=_algo[0], shape=_shape[0]
            )
        except ValueError as exc:
            print(f"Generation error: {exc}", file=sys.stderr)
            return None
        grid: List[List[int]] = gen.to_hex_format()
        blocked: Set[Tuple[int, int]] = gen.blocked_cells
        outside: Set[Tuple[int, int]] = gen.outside_cells
        sol_str: Optional[str] = solve_maze(grid, eff_entry, eff_exit)
        sol_cells: Optional[List[Tuple[int, int]]] = None
        if sol_str:
            sol_cells = _solution_to_cells(eff_entry, sol_str)
        return grid, sol_cells, blocked, outside

    # --- Initial generation -------------------------------------------------
    result = _generate_and_solve(_seed[0])
    if result is None:
        sys.exit(1)
    hex_grid, solution_cells, blocked_cells, outside_cells = result
    solution_str: Optional[str] = solve_maze(hex_grid, _entry[0], _exit[0])

    # --- Write initial output -----------------------------------------------
    try:
        write_output(output_path, hex_grid, entry, exit_cell, solution_str)
        print(f"Output written to {output_path}")
    except OSError as exc:
        print(f"Error writing output: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Regenerate callback (used by both UIs) -----------------------------
    def regenerate_callback() -> Optional[tuple]:  # type: ignore[type-arg]
        """Bump seed, re-generate; return (grid, sol, blocked, outside)."""
        _seed[0] += 1
        res = _generate_and_solve(_seed[0])
        if res is None:
            return None
        new_grid, new_sol, new_blocked, new_outside = res
        new_sol_str: Optional[str] = solve_maze(new_grid, _entry[0], _exit[0])
        try:
            write_output(output_path, new_grid, _entry[0], _exit[0], new_sol_str)
        except OSError:
            pass
        return new_grid, new_sol, new_blocked, new_outside

    def change_algo_callback() -> Optional[tuple]:  # type: ignore[type-arg]
        """Toggle algorithm; return (grid, sol, blocked, outside, label)."""
        _algo[0] = "prims" if _algo[0] == "backtracker" else "backtracker"
        _seed[0] += 1
        res = _generate_and_solve(_seed[0])
        if res is None:
            return None
        new_grid, new_sol, new_blocked, new_outside = res
        new_sol_str: Optional[str] = solve_maze(new_grid, _entry[0], _exit[0])
        try:
            write_output(output_path, new_grid, _entry[0], _exit[0], new_sol_str)
        except OSError:
            pass
        return new_grid, new_sol, new_blocked, new_outside, _ALGO_LABELS[_algo[0]]

    def change_shape_callback() -> Optional[tuple]:  # type: ignore[type-arg]
        """Toggle shape; auto-adjust entry/exit for diamond; return 7-tuple."""
        _shape[0] = "diamond" if _shape[0] == "rectangle" else "rectangle"
        if _shape[0] == "diamond":
            # Use top / bottom vertices of the diamond.
            _entry[0] = (0, width // 2)
            _exit[0] = (height - 1, width // 2)
        else:
            _entry[0] = _orig_entry
            _exit[0] = _orig_exit
        _seed[0] += 1
        res = _generate_and_solve(_seed[0])
        if res is None:
            return None
        new_grid, new_sol, new_blocked, new_outside = res
        new_sol_str: Optional[str] = solve_maze(new_grid, _entry[0], _exit[0])
        try:
            write_output(output_path, new_grid, _entry[0], _exit[0], new_sol_str)
        except OSError:
            pass
        return (
            new_grid, new_sol, new_blocked, new_outside,
            _entry[0], _exit[0], _SHAPE_LABELS[_shape[0]]
        )

    # --- Animation callbacks (graphical UI only) ----------------------------

    def _make_anim_iter(seed: int) -> Optional[tuple]:  # type: ignore[type-arg]
        """Create a step iterator for animated generation.

        Returns an 8-tuple:
            (step_iter, first_grid, blocked, outside,
             entry, exit, algo_label, shape_label)
        or None on error.
        """
        try:
            gen: MazeGenerator = MazeGenerator(
                width=width, height=height, seed=seed,
                perfect=perfect, algorithm=_algo[0], shape=_shape[0],
            )
        except ValueError as exc:
            print(f"Generation error: {exc}", file=sys.stderr)
            return None
        step_iter = gen.iter_generation()
        first_grid: List[List[int]] = next(step_iter)  # triggers setup
        return (
            step_iter, first_grid,
            gen.blocked_cells, gen.outside_cells,
            _entry[0], _exit[0],
            _ALGO_LABELS[_algo[0]], _SHAPE_LABELS[_shape[0]],
        )

    def anim_regen_cb() -> Optional[tuple]:  # type: ignore[type-arg]
        """Bump seed, return animation 8-tuple."""
        _seed[0] += 1
        return _make_anim_iter(_seed[0])

    def anim_algo_cb() -> Optional[tuple]:  # type: ignore[type-arg]
        """Toggle algorithm, bump seed, return animation 8-tuple."""
        _algo[0] = "prims" if _algo[0] == "backtracker" else "backtracker"
        _seed[0] += 1
        return _make_anim_iter(_seed[0])

    def anim_shape_cb() -> Optional[tuple]:  # type: ignore[type-arg]
        """Toggle shape, adjust entry/exit, bump seed, return 8-tuple."""
        _shape[0] = "diamond" if _shape[0] == "rectangle" else "rectangle"
        if _shape[0] == "diamond":
            _entry[0] = (0, width // 2)
            _exit[0] = (height - 1, width // 2)
        else:
            _entry[0] = _orig_entry
            _exit[0] = _orig_exit
        _seed[0] += 1
        return _make_anim_iter(_seed[0])

    def solve_cb(
        grid: List[List[int]],
        eff_entry: Tuple[int, int],
        eff_exit: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """Solve the maze and write output; called after animation ends."""
        sol_str: Optional[str] = solve_maze(grid, eff_entry, eff_exit)
        try:
            write_output(output_path, grid, eff_entry, eff_exit, sol_str)
        except OSError:
            pass
        if sol_str:
            return _solution_to_cells(eff_entry, sol_str)
        return []

    # --- Display ------------------------------------------------------------
    display_mode: str = settings.get("displaymode", "terminal")

    if display_mode == "graphical":
        try:
            from ui.graphical import GraphicalUI
            gui: GraphicalUI = GraphicalUI(
                hex_grid,
                settings=settings,
                solution_path=solution_cells,
                entry=_entry[0],
                exit_cell=_exit[0],
                blocked_cells=blocked_cells,
                outside_cells=outside_cells,
                anim_regen_cb=anim_regen_cb,
                anim_algo_cb=anim_algo_cb,
                anim_shape_cb=anim_shape_cb,
                solve_cb=solve_cb,
                current_algo=_ALGO_LABELS[_algo[0]],
                current_shape=_SHAPE_LABELS[_shape[0]],
            )
            gui.run()
        except ImportError:
            print("MLX not available, falling back to terminal.", file=sys.stderr)
            display_mode = "terminal"

    if display_mode == "terminal":
        ui: TerminalUI = TerminalUI(
            hex_grid,
            settings=settings,
            solution_path=solution_cells,
            entry=_entry[0],
            exit_cell=_exit[0],
            blocked_cells=blocked_cells,
            outside_cells=outside_cells,
            regenerate_callback=regenerate_callback,
            change_algo_callback=change_algo_callback,
            change_shape_callback=change_shape_callback,
            current_algo=_ALGO_LABELS[_algo[0]],
            current_shape=_SHAPE_LABELS[_shape[0]],
        )
        ui.interactive()


if __name__ == "__main__":
    main()
