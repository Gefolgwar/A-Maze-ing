"""Graphical maze rendering with pygame — animated generation + play mode."""

from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple

try:
    import pygame
    _HAS_PYGAME: bool = True
except ImportError:
    _HAS_PYGAME = False

NORTH: int = 0
EAST: int = 1
SOUTH: int = 2
WEST: int = 3

_DIR_DELTA: Dict[int, Tuple[int, int]] = {
    NORTH: (-1, 0), EAST: (0, 1), SOUTH: (1, 0), WEST: (0, -1)
}


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h: str = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


_COLOR_PRESETS: List[Dict[str, str]] = [
    {"WallColor": "#FFFFFF", "SolutionColor": "#FF0000", "PathColor": "#00FF00"},
    {"WallColor": "#00AAFF", "SolutionColor": "#FFAA00", "PathColor": "#AAFFAA"},
    {"WallColor": "#FF00FF", "SolutionColor": "#00FFFF", "PathColor": "#FFFF00"},
]

_BLOCKED_COLOR: Tuple[int, int, int] = (80, 80, 80)
_MENU_BG: Tuple[int, int, int] = (25, 25, 25)
_MENU_FG: Tuple[int, int, int] = (220, 220, 220)
_MENU_HL: Tuple[int, int, int] = (255, 220, 50)
_ANIM_COLOR: Tuple[int, int, int] = (0, 200, 255)
_GAME_COLOR: Tuple[int, int, int] = (50, 220, 50)
_PLAYER_COLOR: Tuple[int, int, int] = (255, 200, 0)        # player cell
_WIN_COLOR: Tuple[int, int, int] = (0, 255, 128)            # win highlight

_MIN_SPEED: int = 1
_MAX_SPEED: int = 128


class GraphicalUI:
    """Pygame maze renderer.

    Maze build keys:
        1/R Re-gen   2 Algo   3 Shape   +/- speed
        4/P path     5/C colors   6/Q/Esc quit
    Play mode (toggle with G):
        Arrow keys to move, step counter shown in menu.
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
        anim_regen_cb: Optional[  # type: ignore[type-arg]
            Callable[[], Optional[tuple]]
        ] = None,
        anim_algo_cb: Optional[  # type: ignore[type-arg]
            Callable[[], Optional[tuple]]
        ] = None,
        anim_shape_cb: Optional[  # type: ignore[type-arg]
            Callable[[], Optional[tuple]]
        ] = None,
        solve_cb: Optional[  # type: ignore[type-arg]
            Callable[..., List[Tuple[int, int]]]
        ] = None,
        current_algo: str = "Recursive Backtracker",
        current_shape: str = "Rectangle",
    ) -> None:
        if not _HAS_PYGAME:
            raise ImportError("pygame is required. pip install pygame")

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

        self.anim_regen_cb = anim_regen_cb
        self.anim_algo_cb = anim_algo_cb
        self.anim_shape_cb = anim_shape_cb
        self.solve_cb = solve_cb
        self.current_algo: str = current_algo
        self.current_shape: str = current_shape

        # Animation state
        self._anim_iter: Optional[Iterator[List[List[int]]]] = None
        self._is_animating: bool = False
        self.anim_speed: int = 5
        self._anim_entry: Optional[Tuple[int, int]] = entry
        self._anim_exit: Optional[Tuple[int, int]] = exit_cell

        # Play-mode state
        self._game_mode: bool = False
        self._player_pos: Optional[Tuple[int, int]] = entry
        self._player_steps: int = 0
        self._game_won: bool = False

        # Rendering
        self.cell_size: int = int(self.settings.get("cellsize", "20"))
        self.bg_color: Tuple[int, int, int] = _hex_to_rgb(
            self.settings.get("backgroundcolor", "#000000")
        )
        self._preset_idx: int = 0
        self.wall_color: Tuple[int, int, int] = (255, 255, 255)
        self.solution_color: Tuple[int, int, int] = (255, 0, 0)
        self.path_color: Tuple[int, int, int] = (0, 255, 0)
        self._apply_preset()

    # ── Colour ───────────────────────────────────────────────────────────

    def _apply_preset(self) -> None:
        p: Dict[str, str] = _COLOR_PRESETS[self._preset_idx]
        self.wall_color = _hex_to_rgb(p["WallColor"])
        self.solution_color = _hex_to_rgb(p["SolutionColor"])
        self.path_color = _hex_to_rgb(p["PathColor"])

    def _cycle_colors(self) -> None:
        self._preset_idx = (self._preset_idx + 1) % len(_COLOR_PRESETS)
        self._apply_preset()

    # ── Play mode ─────────────────────────────────────────────────────────

    def _toggle_game_mode(self) -> None:
        """Toggle play mode on/off; reset player to entry."""
        if self._is_animating:
            return
        self._game_mode = not self._game_mode
        if self._game_mode:
            self._player_pos = self.entry
            self._player_steps = 0
            self._game_won = False

    def _handle_player_move(self, direction: int) -> None:
        """Try to move the player one step in *direction*."""
        if not self._game_mode or self._game_won:
            return
        if self._player_pos is None:
            return
        r, c = self._player_pos
        cell: int = self.hex_grid[r][c]
        if not (cell & (1 << direction)):
            return  # wall blocks movement
        dr, dc = _DIR_DELTA[direction]
        nr, nc = r + dr, c + dc
        if (
            0 <= nr < self.height
            and 0 <= nc < self.width
            and (nr, nc) not in self.outside_cells
            and (nr, nc) not in self.blocked_cells
        ):
            self._player_pos = (nr, nc)
            self._player_steps += 1
            if (nr, nc) == self.exit_cell:
                self._game_won = True

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self) -> None:
        pygame.init()
        _MENU_W: int = 220
        maze_w: int = self.width * self.cell_size + 1
        maze_h: int = self.height * self.cell_size + 1
        win_w: int = maze_w + _MENU_W
        win_h: int = max(maze_h, 370)
        screen: pygame.Surface = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption("A-Maze-Ing")
        font: pygame.font.Font = pygame.font.SysFont("consolas", 15)
        clock: pygame.time.Clock = pygame.time.Clock()

        running: bool = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    k = event.key
                    # Arrow keys — play mode movement
                    if self._game_mode:
                        if k == pygame.K_UP:
                            self._handle_player_move(NORTH)
                        elif k == pygame.K_RIGHT:
                            self._handle_player_move(EAST)
                        elif k == pygame.K_DOWN:
                            self._handle_player_move(SOUTH)
                        elif k == pygame.K_LEFT:
                            self._handle_player_move(WEST)
                    # Global keys
                    if k in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif k == pygame.K_g:
                        self._toggle_game_mode()
                    elif not self._game_mode:
                        if k in (pygame.K_1, pygame.K_r):
                            self._trigger_anim(self.anim_regen_cb)
                        elif k == pygame.K_2:
                            self._trigger_anim(self.anim_algo_cb)
                        elif k == pygame.K_3:
                            self._trigger_anim(self.anim_shape_cb)
                        elif k in (pygame.K_5, pygame.K_c):
                            self._cycle_colors()
                        elif k in (pygame.K_EQUALS, pygame.K_PLUS):
                            self.anim_speed = min(
                                _MAX_SPEED, self.anim_speed * 2
                            )
                        elif k == pygame.K_MINUS:
                            self.anim_speed = max(
                                _MIN_SPEED, self.anim_speed // 2
                            )
                    # Key 4 / P works in both normal and game mode
                    if k in (pygame.K_4, pygame.K_p) and not self._is_animating:
                        self.show_solution = not self.show_solution
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if mx > maze_w:
                        self._handle_menu_click(my, font)

            if self._is_animating and self._anim_iter is not None:
                if self._advance_anim():
                    self._finish_anim()

            screen.fill(self.bg_color)
            self._draw_maze(screen)
            self._draw_menu(screen, maze_w, win_h, font)
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    # ── Animation control ─────────────────────────────────────────────────

    def _trigger_anim(self, callback: Optional[object]) -> None:
        if not callable(callback):
            return
        result = callback()  # type: ignore[operator]
        if result is None:
            return
        (
            step_iter, first_grid,
            blocked, outside,
            entry, exit_,
            algo_label, shape_label,
        ) = result
        self.hex_grid = first_grid
        self.blocked_cells = blocked
        self.outside_cells = outside
        self._anim_entry = entry
        self._anim_exit = exit_
        self.current_algo = algo_label
        self.current_shape = shape_label
        self.solution_cells = set()
        self._anim_iter = iter(step_iter)
        self._is_animating = True
        # Reset play mode when re-generating
        self._game_mode = False
        self._game_won = False

    def _advance_anim(self) -> bool:
        assert self._anim_iter is not None
        for _ in range(self.anim_speed):
            try:
                self.hex_grid = next(self._anim_iter)
            except StopIteration:
                return True
        return False

    def _finish_anim(self) -> None:
        self._anim_iter = None
        self._is_animating = False
        self.entry = self._anim_entry
        self.exit_cell = self._anim_exit
        self._player_pos = self.entry
        if callable(self.solve_cb) and self.entry and self.exit_cell:
            cells = self.solve_cb(  # type: ignore[operator]
                self.hex_grid, self.entry, self.exit_cell
            )
            self.solution_cells = set(cells or [])

    # ── Menu ─────────────────────────────────────────────────────────────

    def _handle_menu_click(self, y: int, font: pygame.font.Font) -> None:
        actions = [
            lambda: self._trigger_anim(self.anim_regen_cb),
            lambda: self._trigger_anim(self.anim_algo_cb),
            lambda: self._trigger_anim(self.anim_shape_cb),
            lambda: setattr(self, "show_solution", not self.show_solution),
            self._cycle_colors,
            self._toggle_game_mode,
        ]
        start_y, item_h = 80, 34
        for i, action in enumerate(actions):
            if start_y + i * item_h <= y < start_y + (i + 1) * item_h:
                # In game mode only path-toggle (i=3) and game-toggle (i=5) allowed
                if self._game_mode and i not in (3, 5):
                    return
                if i == 3 and self._is_animating:
                    return
                action()
                break

    def _draw_menu(
        self,
        screen: pygame.Surface,
        x_offset: int,
        win_h: int,
        font: pygame.font.Font,
    ) -> None:
        pygame.draw.rect(screen, _MENU_BG, (x_offset, 0, 220, win_h))
        pygame.draw.line(
            screen, (100, 100, 100), (x_offset, 0), (x_offset, win_h)
        )

        # Title
        if self._game_mode:
            title = "PLAY MODE"
            title_col = _GAME_COLOR
        elif self._is_animating:
            title = "BUILDING..."
            title_col = _ANIM_COLOR
        else:
            title = "A-Maze-ing"
            title_col = _MENU_HL
        screen.blit(font.render(title, True, title_col), (x_offset + 4, 6))

        # Speed
        speed_col = _ANIM_COLOR if self._is_animating else _MENU_FG
        screen.blit(
            font.render(
                f"+/- Speed: {self.anim_speed} step/fr", True, speed_col
            ),
            (x_offset + 4, 26),
        )
        pygame.draw.line(
            screen, (60, 60, 60), (x_offset + 4, 56), (x_offset + 216, 56)
        )

        algo_short: str = self.current_algo[:13]
        shape_short: str = self.current_shape[:10]
        items = [
            "1. Re-generate",
            f"2. Algo: {algo_short}",
            f"3. Shape: {shape_short}",
            "4. Show/Hide path",
            "5. Rotate colors",
            f"G. Game: {'ON' if self._game_mode else 'OFF'}",
            "Q/Esc. Quit",
        ]
        start_y, item_h = 80, 34
        for i, label in enumerate(items):
            if self._game_mode and i == 5:
                col = _GAME_COLOR
            elif self._is_animating and i < 3:
                col = _ANIM_COLOR
            else:
                col = _MENU_FG
            screen.blit(
                font.render(label, True, col),
                (x_offset + 8, start_y + i * item_h),
            )

        # Play-mode stats
        if self._game_mode:
            sep_y: int = start_y + len(items) * item_h + 6
            pygame.draw.line(
                screen, (60, 60, 60),
                (x_offset + 4, sep_y), (x_offset + 216, sep_y)
            )
            steps_label: str = f"Steps: {self._player_steps}"
            steps_col = _WIN_COLOR if self._game_won else _GAME_COLOR
            screen.blit(
                font.render(steps_label, True, steps_col),
                (x_offset + 8, sep_y + 6),
            )
            if self._game_won:
                screen.blit(
                    font.render("*** YOU WIN! ***", True, _WIN_COLOR),
                    (x_offset + 8, sep_y + 26),
                )
                screen.blit(
                    font.render(
                        "Press G to play again", True, _MENU_FG
                    ),
                    (x_offset + 8, sep_y + 46),
                )
            else:
                screen.blit(
                    font.render(
                        "Arrows: navigate", True, _MENU_FG
                    ),
                    (x_offset + 8, sep_y + 26),
                )

    # ── Maze drawing ─────────────────────────────────────────────────────

    def _draw_maze(self, screen: pygame.Surface) -> None:
        cs: int = self.cell_size
        for r in range(self.height):
            for c in range(self.width):
                if (r, c) in self.outside_cells:
                    continue
                x: int = c * cs
                y: int = r * cs
                cell: int = self.hex_grid[r][c]

                # Fill
                if (r, c) in self.blocked_cells:
                    pygame.draw.rect(
                        screen, _BLOCKED_COLOR, (x + 1, y + 1, cs - 1, cs - 1)
                    )
                elif self._game_mode and (r, c) == self._player_pos:
                    col = _WIN_COLOR if self._game_won else _PLAYER_COLOR
                    pygame.draw.rect(
                        screen, col, (x + 2, y + 2, cs - 3, cs - 3)
                    )
                elif (r, c) in (self.entry, self.exit_cell):
                    pygame.draw.rect(
                        screen, self.path_color,
                        (x + 1, y + 1, cs - 1, cs - 1)
                    )
                elif self.show_solution and (r, c) in self.solution_cells:
                    pygame.draw.rect(
                        screen, self.solution_color,
                        (x + 1, y + 1, cs - 1, cs - 1)
                    )

                # Walls
                if not (cell & (1 << NORTH)):
                    pygame.draw.line(
                        screen, self.wall_color, (x, y), (x + cs, y)
                    )
                if not (cell & (1 << EAST)):
                    pygame.draw.line(
                        screen, self.wall_color,
                        (x + cs, y), (x + cs, y + cs)
                    )
                if not (cell & (1 << SOUTH)):
                    pygame.draw.line(
                        screen, self.wall_color,
                        (x, y + cs), (x + cs, y + cs)
                    )
                if not (cell & (1 << WEST)):
                    pygame.draw.line(
                        screen, self.wall_color, (x, y), (x, y + cs)
                    )
