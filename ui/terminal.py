"""Terminal-based ASCII maze rendering with colorama support."""

from typing import Dict, List, Optional, Set, Tuple

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    _HAS_COLORAMA: bool = True
except ImportError:
    _HAS_COLORAMA = False

_FG: Dict[str, str] = {}
_RESET: str = ""

if _HAS_COLORAMA:
    _FG = {
        "#FFFFFF": Fore.WHITE,
        "#00FF00": Fore.GREEN,
        "#FF0000": Fore.RED,
        "#000000": Fore.BLACK,
        "#FFFF00": Fore.YELLOW,
        "#0000FF": Fore.BLUE,
        "#FF00FF": Fore.MAGENTA,
        "#00FFFF": Fore.CYAN,
    }
    _RESET = Style.RESET_ALL

NORTH: int = 0
EAST: int = 1
SOUTH: int = 2
WEST: int = 3

_COLOR_SCHEMES: List[Dict[str, str]] = [
    {"WallColor": "#FFFFFF", "PathColor": "#00FF00", "SolutionColor": "#FF0000"},
    {"WallColor": "#0000FF", "PathColor": "#FFFF00", "SolutionColor": "#FF00FF"},
    {"WallColor": "#00FFFF", "PathColor": "#FFFFFF", "SolutionColor": "#00FF00"},
]


def _fc(hex_color: str) -> str:
    """Return colorama foreground ANSI code for a hex color."""
    return _FG.get(hex_color.upper(), "")


class TerminalUI:
    """ASCII maze renderer with numbered menu (1-6) for the terminal.

    Blocked ``42`` cells render as dim ``▓▓``; cells outside the maze
    shape (e.g. diamond corners) render as blank.
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
        self._scheme_index: int = 0
        self.wall_color: str = ""
        self.path_color: str = ""
        self.sol_color: str = ""
        self._apply_scheme()

    def _apply_scheme(self) -> None:
        scheme: Dict[str, str] = _COLOR_SCHEMES[self._scheme_index]
        self.wall_color = scheme["WallColor"]
        self.path_color = scheme["PathColor"]
        self.sol_color = scheme["SolutionColor"]

    def render(self) -> str:
        """Render the maze as an ASCII string."""
        wc: str = _fc(self.wall_color)
        pc: str = _fc(self.path_color)
        sc: str = _fc(self.sol_color)
        grey: str = (Fore.WHITE + Style.DIM) if _HAS_COLORAMA else ""
        lines: List[str] = []

        for r in range(self.height):
            # ── Top wall row ──────────────────────────────────────────
            top: str = ""
            for c in range(self.width):
                if (r, c) in self.outside_cells:
                    top += "   "
                else:
                    cell: int = self.hex_grid[r][c]
                    has_north: bool = not bool(cell & (1 << NORTH))
                    top += wc + "+" + ("--" if has_north else "  ") + _RESET
            last: int = self.width - 1
            top += " " if (r, last) in self.outside_cells else wc + "+" + _RESET
            lines.append(top)

            # ── Cell content row ──────────────────────────────────────
            mid: str = ""
            for c in range(self.width):
                if (r, c) in self.outside_cells:
                    mid += "   "
                else:
                    cell = self.hex_grid[r][c]
                    has_west: bool = not bool(cell & (1 << WEST))
                    mid += wc + ("|" if has_west else " ") + _RESET
                    if (r, c) in self.blocked_cells:
                        mid += grey + "▓▓" + _RESET
                    elif (r, c) == self.entry:
                        mid += pc + "EN" + _RESET
                    elif (r, c) == self.exit_cell:
                        mid += pc + "EX" + _RESET
                    elif self.show_solution and (r, c) in self.solution_cells:
                        mid += sc + "##" + _RESET
                    else:
                        mid += "  "
            if (r, last) in self.outside_cells:
                mid += " "
            else:
                last_cell: int = self.hex_grid[r][last]
                has_east: bool = not bool(last_cell & (1 << EAST))
                mid += wc + ("|" if has_east else " ") + _RESET
            lines.append(mid)

        # ── Bottom wall row ───────────────────────────────────────────
        bottom: str = ""
        last_row: int = self.height - 1
        for c in range(self.width):
            if (last_row, c) in self.outside_cells:
                bottom += "   "
            else:
                cell = self.hex_grid[last_row][c]
                has_south: bool = not bool(cell & (1 << SOUTH))
                bottom += wc + "+" + ("--" if has_south else "  ") + _RESET
        last = self.width - 1
        bottom += (
            " " if (last_row, last) in self.outside_cells
            else wc + "+" + _RESET
        )
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
        print("5. Rotate maze colors")
        print("6. Quit")

    def _set_grid(self, res: tuple) -> None:
        """Unpack (grid, sol, blocked, outside[, label...]) into self."""
        self.hex_grid, sol, self.blocked_cells, self.outside_cells = res[:4]
        self.height = len(self.hex_grid)
        self.width = len(self.hex_grid[0]) if self.height > 0 else 0
        self.solution_cells = set(sol or [])
        # Optional extra fields differ per callback.
        if len(res) >= 6:  # shape callback returns entry/exit too
            self.entry, self.exit_cell = res[4], res[5]

    def interactive(self) -> None:
        """Run the interactive numbered-menu loop."""
        while True:
            self.display()
            self._print_menu()
            try:
                choice: str = input("Choice? (1-6): ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "1":
                if callable(self.regenerate_callback):
                    res = self.regenerate_callback()  # type: ignore[operator]
                    if res is not None:
                        self._set_grid(res)
            elif choice == "2":
                if callable(self.change_algo_callback):
                    res = self.change_algo_callback()  # type: ignore[operator]
                    if res is not None:
                        self._set_grid(res)
                        self.current_algo = res[4]
            elif choice == "3":
                if callable(self.change_shape_callback):
                    res = self.change_shape_callback()  # type: ignore[operator]
                    if res is not None:
                        self._set_grid(res)
                        self.current_shape = res[6]
            elif choice == "4":
                self.show_solution = not self.show_solution
            elif choice == "5":
                self._scheme_index = (self._scheme_index + 1) % len(_COLOR_SCHEMES)
                self._apply_scheme()
            elif choice == "6":
                break
