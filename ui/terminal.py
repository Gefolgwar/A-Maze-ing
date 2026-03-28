"""Terminal-based ASCII maze rendering (Plain Text Version)."""

from typing import Any, Dict, List, Optional, Set, Tuple

NORTH: int = 0
EAST: int = 1
SOUTH: int = 2
WEST: int = 3


class TerminalUI:
    """ASCII maze renderer with numbered menu (1-6) for the terminal.

    Blocked cells render as '▓▓'; cells outside the maze
    shape render as blank.
    """

    def __init__(
        self,
        hex_grid: List[List[int]],
        settings: Optional[Dict[str, str]] = None,
        solution_path: Optional[List[Tuple[int, int]]] = None,
        entry: Optional[Tuple[int, int]] = None,
        exit_cell: Optional[Tuple[int, int]] = None,
        blocked_cells: Optional[Set[Tuple[int, int]]] = None,
        outside_cells: Optional[Set[Tuple[int, int]]] = None,
        regenerate_callback: Optional[object] = None,
        change_algo_callback: Optional[object] = None,
        change_shape_callback: Optional[object] = None,
        current_algo: str = "Recursive Backtracker",
        current_shape: str = "Rectangle",
    ) -> None:
        self.hex_grid: List[List[int]] = hex_grid
        self.height: int = len(hex_grid)
        self.width: int = len(hex_grid[0]) if self.height > 0 else 0
        self.settings: Dict[str, str] = settings or {}
        self.solution_cells: Set[Tuple[int, int]] = set(solution_path or [])
        self.show_solution: bool = True
        self.entry: Optional[Tuple[int, int]] = entry
        self.exit_cell: Optional[Tuple[int, int]] = exit_cell
        self.blocked_cells: Set[Tuple[int, int]] = blocked_cells or set()
        self.outside_cells: Set[Tuple[int, int]] = outside_cells or set()
        self.regenerate_callback: Optional[object] = regenerate_callback
        self.change_algo_callback: Optional[object] = change_algo_callback
        self.change_shape_callback: Optional[object] = change_shape_callback
        self.current_algo: str = current_algo
        self.current_shape: str = current_shape

    def render(self) -> str:
        """Render the maze as an ASCII string."""
        lines: List[str] = []

        for r in range(self.height):
            # ── Top wall row ──────────────────────────────────────────
            top: str = ""
            for c in range(self.width):
                if (r, c) in self.outside_cells:
                    top += "   "
                else:
                    cell: int = self.hex_grid[r][c]
                    has_north: bool = bool(cell & (1 << NORTH))
                    top += "+" + ("--" if has_north else "  ")
            last: int = self.width - 1
            top += " " if (r, last) in self.outside_cells else "+"
            lines.append(top)

            # ── Cell content row ──────────────────────────────────────
            mid: str = ""
            for c in range(self.width):
                if (r, c) in self.outside_cells:
                    mid += "   "
                else:
                    cell = self.hex_grid[r][c]
                    has_west: bool = bool(cell & (1 << WEST))
                    mid += ("|" if has_west else " ")
                    if (r, c) in self.blocked_cells:
                        mid += "▓▓"
                    elif (r, c) == self.entry:
                        mid += "EN"
                    elif (r, c) == self.exit_cell:
                        mid += "EX"
                    elif self.show_solution and (r, c) in self.solution_cells:
                        mid += "##"
                    else:
                        mid += "  "

            if (r, last) in self.outside_cells:
                mid += " "
            else:
                last_cell: int = self.hex_grid[r][last]
                has_east: bool = bool(last_cell & (1 << EAST))
                mid += ("|" if has_east else " ")
            lines.append(mid)

        # ── Bottom wall row ───────────────────────────────────────────
        bottom: str = ""
        last_row: int = self.height - 1
        for c in range(self.width):
            if (last_row, c) in self.outside_cells:
                bottom += "   "
            else:
                cell = self.hex_grid[last_row][c]
                has_south: bool = bool(cell & (1 << SOUTH))
                bottom += "+" + ("--" if has_south else "  ")
        last = self.width - 1
        bottom += " " if (last_row, last) in self.outside_cells else "+"
        lines.append(bottom)

        return "\n".join(lines)

    def display(self) -> None:
        """Print the rendered maze to stdout."""
        print(self.render())

    def _print_menu(self) -> None:
        print("\n=== A-Maze-ing ===")
        print("1. Re-generate a new maze")
        print(f"2. Change algorithm (Current: {self.current_algo})")
        print(f"3. Change shape     (Current: {self.current_shape})")
        print("4. Show/Hide path from entry to exit")
        print("5. Quit")

    def _set_grid(self, res: Tuple[Any, ...]) -> None:
        """Unpack (grid, sol, blocked, outside[, label...]) into self."""
        self.hex_grid, sol, self.blocked_cells, self.outside_cells = res[:4]
        self.height = len(self.hex_grid)
        self.width = len(self.hex_grid[0]) if self.height > 0 else 0
        self.solution_cells = set(sol or [])
        if len(res) >= 6:
            self.entry, self.exit_cell = res[4], res[5]

    def interactive(self) -> None:
        """Run the interactive numbered-menu loop."""
        while True:
            self.display()
            self._print_menu()
            try:
                choice: str = input("Choice? (1-5): ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "1":
                if callable(self.regenerate_callback):
                    res = self.regenerate_callback()
                    if res is not None:
                        self._set_grid(res)
            elif choice == "2":
                if callable(self.change_algo_callback):
                    res = self.change_algo_callback()
                    if res is not None:
                        self._set_grid(res)
                        self.current_algo = res[4]
            elif choice == "3":
                if callable(self.change_shape_callback):
                    res = self.change_shape_callback()
                    if res is not None:
                        self._set_grid(res)
                        self.current_shape = res[6]
            elif choice == "4":
                self.show_solution = not self.show_solution
            elif choice == "5":
                break
