"""Graphical maze rendering with MiniLibX (MLX) — animated generation + play mode."""

from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple

try:
    from mlx.mlx import Mlx
    _HAS_MLX: bool = True
except ImportError:
    _HAS_MLX = False

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


def _rgb_to_color(r: int, g: int, b: int) -> int:
    """Pack RGB into MLX colour integer (0x00RRGGBB)."""
    return (r << 16) | (g << 8) | b


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
_PLAYER_COLOR: Tuple[int, int, int] = (255, 200, 0)
_WIN_COLOR: Tuple[int, int, int] = (0, 255, 128)

_MIN_SPEED: int = 1
_MAX_SPEED: int = 128

# ── X11 key syms ─────────────────────────────────────────────────────────
_KEY_ESC: int = 65307
_KEY_Q: int = 113
_KEY_R: int = 114
_KEY_C: int = 99
_KEY_P: int = 112
_KEY_G: int = 103
_KEY_1: int = 49
_KEY_2: int = 50
_KEY_3: int = 51
_KEY_4: int = 52
_KEY_5: int = 53
_KEY_EQUAL: int = 61
_KEY_PLUS_KP: int = 65451
_KEY_MINUS: int = 45
_KEY_MINUS_KP: int = 65453
_KEY_UP: int = 65362
_KEY_DOWN: int = 65364
_KEY_LEFT: int = 65361
_KEY_RIGHT: int = 65363


# ── Module-level callbacks for MLX (CFUNCTYPE-compatible) ─────────────────

def _on_key(keycode: int, state: object) -> None:  # type: ignore[type-arg]
    """Handle key press events."""
    if isinstance(state, GraphicalUI):
        state.handle_key(keycode)




def _on_loop(state: object) -> None:  # type: ignore[type-arg]
    """Idle frame callback — advance animation and redraw."""
    if isinstance(state, GraphicalUI):
        state.handle_frame()


def _on_expose(state: object) -> None:  # type: ignore[type-arg]
    """Expose callback — mark for redraw."""
    if isinstance(state, GraphicalUI):
        state._needs_redraw = True
        state._needs_menu_redraw = True


def _on_destroy(state: object) -> None:  # type: ignore[type-arg]
    """Window close (DestroyNotify) callback."""
    if isinstance(state, GraphicalUI):
        state._quit()


class GraphicalUI:
    """MiniLibX maze renderer.

    Maze build keys:
        1/R Re-gen   2 Algo   3 Shape   +/- speed
        4/P path     5/C colors   Q/Esc quit
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
        if not _HAS_MLX:
            raise ImportError("MLX is required. Install the mlx wheel.")

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

        # MLX state (initialised in run())
        self._mlx: Optional[object] = None
        self._mlx_ptr: Optional[object] = None
        self._win_ptr: Optional[object] = None
        # Maze image — covers only the maze area, blitted every frame.
        self._img_ptr: Optional[object] = None
        self._img_data: Optional[memoryview] = None
        self._img_bpp: int = 0
        self._img_sl: int = 0
        self._img_fmt: int = 0
        # Menu image — covers only the side-panel, blitted on menu changes.
        self._menu_img_ptr: Optional[object] = None
        self._menu_img_data: Optional[memoryview] = None
        self._menu_img_sl: int = 0
        self._maze_w: int = 0
        self._maze_h: int = 0
        self._win_w: int = 0
        self._win_h: int = 0
        self._menu_w: int = 240
        self._needs_redraw: bool = True
        self._needs_menu_redraw: bool = True

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
        if cell & (1 << direction):
            return  # wall blocks movement (bit=1 → closed)
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

    # ── Image buffer drawing ─────────────────────────────────────────────

    def _pixel_bytes(self, r: int, g: int, b: int) -> bytes:
        """Return the 4-byte pixel value for the current image format."""
        if self._img_fmt == 0:  # B8G8R8A8
            return bytes([b, g, r, 255])
        return bytes([255, r, g, b])  # A8R8G8B8

    def _put_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        """Set a single pixel in the maze image buffer."""
        if x < 0 or x >= self._maze_w or y < 0 or y >= self._win_h:
            return
        bpp: int = self._img_bpp // 8
        off: int = y * self._img_sl + x * bpp
        px: bytes = self._pixel_bytes(r, g, b)
        self._img_data[off:off + 4] = px  # type: ignore[index]

    def _fill_rect(
        self, x: int, y: int, w: int, h: int,
        r: int, g: int, b: int,
        *, img_data: Optional[memoryview] = None,
        img_w: Optional[int] = None, img_sl: Optional[int] = None,
    ) -> None:
        """Fill a rectangle in an image buffer (defaults to maze image)."""
        data = img_data if img_data is not None else self._img_data
        max_w = img_w if img_w is not None else self._maze_w
        sl = img_sl if img_sl is not None else self._img_sl
        x1: int = max(0, x)
        y1: int = max(0, y)
        x2: int = min(max_w, x + w)
        y2: int = min(self._win_h, y + h)
        if x2 <= x1 or y2 <= y1:
            return
        bpp: int = self._img_bpp // 8
        px: bytes = self._pixel_bytes(r, g, b)
        row: bytes = px * (x2 - x1)
        row_len: int = len(row)
        for py in range(y1, y2):
            off: int = py * sl + x1 * bpp
            data[off:off + row_len] = row  # type: ignore[index]

    def _draw_hline(
        self, x1: int, x2: int, y: int, r: int, g: int, b: int,
        *, img_data: Optional[memoryview] = None,
        img_w: Optional[int] = None, img_sl: Optional[int] = None,
    ) -> None:
        """Draw a horizontal line in an image buffer (defaults to maze image)."""
        data = img_data if img_data is not None else self._img_data
        max_w = img_w if img_w is not None else self._maze_w
        sl = img_sl if img_sl is not None else self._img_sl
        if y < 0 or y >= self._win_h:
            return
        xa: int = max(0, min(x1, x2))
        xb: int = min(max_w - 1, max(x1, x2))
        if xa > xb:
            return
        bpp: int = self._img_bpp // 8
        px: bytes = self._pixel_bytes(r, g, b)
        row: bytes = px * (xb - xa + 1)
        off: int = y * sl + xa * bpp
        data[off:off + len(row)] = row  # type: ignore[index]

    def _draw_vline(
        self, x: int, y1: int, y2: int, r: int, g: int, b: int,
        *, img_data: Optional[memoryview] = None,
        img_w: Optional[int] = None, img_sl: Optional[int] = None,
    ) -> None:
        """Draw a vertical line in an image buffer (defaults to maze image)."""
        data = img_data if img_data is not None else self._img_data
        max_w = img_w if img_w is not None else self._maze_w
        sl_val = img_sl if img_sl is not None else self._img_sl
        if x < 0 or x >= max_w:
            return
        ya: int = max(0, min(y1, y2))
        yb: int = min(self._win_h - 1, max(y1, y2))
        if ya > yb:
            return
        bpp: int = self._img_bpp // 8
        px: bytes = self._pixel_bytes(r, g, b)
        for py in range(ya, yb + 1):
            off: int = py * sl_val + x * bpp
            data[off:off + 4] = px  # type: ignore[index]

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self) -> None:
        mlx = Mlx()
        self._mlx = mlx
        self._mlx_ptr = mlx.mlx_init()
        if self._mlx_ptr is None:
            raise RuntimeError("mlx_init() failed")

        self._maze_w = self.width * self.cell_size + 1
        self._maze_h = self.height * self.cell_size + 1
        self._win_w = self._maze_w + self._menu_w
        self._win_h = max(self._maze_h, 410)

        self._win_ptr = mlx.mlx_new_window(
            self._mlx_ptr, self._win_w, self._win_h, "A-Maze-Ing"
        )
        if self._win_ptr is None:
            raise RuntimeError("mlx_new_window() failed")

        # Maze image — covers only the maze area
        self._img_ptr = mlx.mlx_new_image(
            self._mlx_ptr, self._maze_w, self._win_h,
        )
        img_info = mlx.mlx_get_data_addr(self._img_ptr)
        self._img_data = img_info[0]
        self._img_bpp = img_info[1]
        self._img_sl = img_info[2]
        self._img_fmt = img_info[3]

        # Menu image — covers only the side-panel; blitted independently
        self._menu_img_ptr = mlx.mlx_new_image(
            self._mlx_ptr, self._menu_w, self._win_h,
        )
        menu_info = mlx.mlx_get_data_addr(self._menu_img_ptr)
        self._menu_img_data = menu_info[0]
        self._menu_img_sl = menu_info[2]

        # Register hooks
        # Key press (X11 event 2) for responsiveness
        mlx.mlx_hook(self._win_ptr, 2, 1, _on_key, self)
        mlx.mlx_expose_hook(self._win_ptr, _on_expose, self)
        mlx.mlx_loop_hook(self._mlx_ptr, _on_loop, self)
        # Window close (X11 DestroyNotify = event 17)
        mlx.mlx_hook(self._win_ptr, 33, 0, _on_destroy, self)

        self._needs_redraw = True
        self._needs_menu_redraw = True
        mlx.mlx_loop(self._mlx_ptr)

        # Cleanup after loop exits
        mlx.mlx_destroy_image(self._mlx_ptr, self._img_ptr)
        mlx.mlx_destroy_image(self._mlx_ptr, self._menu_img_ptr)
        mlx.mlx_destroy_window(self._mlx_ptr, self._win_ptr)
        mlx.mlx_release(self._mlx_ptr)

    # ── Event handlers ────────────────────────────────────────────────────

    def handle_key(self, keycode: int) -> None:
        """Handle a key press event."""
        # Arrow keys — play mode movement
        if self._game_mode:
            if keycode == _KEY_UP:
                self._handle_player_move(NORTH)
                self._needs_redraw = True
                self._needs_menu_redraw = True
            elif keycode == _KEY_RIGHT:
                self._handle_player_move(EAST)
                self._needs_redraw = True
                self._needs_menu_redraw = True
            elif keycode == _KEY_DOWN:
                self._handle_player_move(SOUTH)
                self._needs_redraw = True
                self._needs_menu_redraw = True
            elif keycode == _KEY_LEFT:
                self._handle_player_move(WEST)
                self._needs_redraw = True
                self._needs_menu_redraw = True

        # Global keys
        if keycode in (_KEY_Q, _KEY_ESC):
            self._quit()
        elif keycode == _KEY_G:
            self._toggle_game_mode()
            self._needs_redraw = True
            self._needs_menu_redraw = True
        elif not self._game_mode:
            if keycode in (_KEY_1, _KEY_R):
                self._trigger_anim(self.anim_regen_cb)
            elif keycode == _KEY_2:
                self._trigger_anim(self.anim_algo_cb)
            elif keycode == _KEY_3:
                self._trigger_anim(self.anim_shape_cb)
            elif keycode in (_KEY_5, _KEY_C):
                self._cycle_colors()
                self._needs_redraw = True
                self._needs_menu_redraw = True
            elif keycode in (_KEY_EQUAL, _KEY_PLUS_KP):
                self.anim_speed = min(_MAX_SPEED, self.anim_speed * 2)
                self._needs_redraw = True
                self._needs_menu_redraw = True
            elif keycode in (_KEY_MINUS, _KEY_MINUS_KP):
                self.anim_speed = max(_MIN_SPEED, self.anim_speed // 2)
                self._needs_redraw = True
                self._needs_menu_redraw = True

        # Key 4 / P works in both modes
        if keycode in (_KEY_4, _KEY_P) and not self._is_animating:
            self.show_solution = not self.show_solution
            self._needs_redraw = True
            self._needs_menu_redraw = True


    def handle_frame(self) -> None:
        """Called on each idle loop iteration."""
        if self._is_animating and self._anim_iter is not None:
            if self._advance_anim():
                self._finish_anim()
                self._needs_menu_redraw = True
            self._needs_redraw = True

        if self._needs_redraw:
            self._redraw()
            self._needs_redraw = False

    def _quit(self) -> None:
        """Exit the MLX loop."""
        if self._mlx is not None and self._mlx_ptr is not None:
            self._mlx.mlx_loop_exit(self._mlx_ptr)  # type: ignore[union-attr]

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
        self._needs_menu_redraw = True

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


    # ── Full redraw ──────────────────────────────────────────────────────

    def _redraw(self) -> None:
        """Redraw the window.

        The maze image is blitted every frame.  The menu image is blitted
        only when its content changes, keeping it completely static during
        maze-generation animation and eliminating flickering.
        """
        mlx = self._mlx
        # ── Maze image (blitted every frame) ──────────────────────────
        self._fill_rect(0, 0, self._maze_w, self._win_h, *self.bg_color)
        self._draw_maze()
        mlx.mlx_put_image_to_window(  # type: ignore[union-attr]
            self._mlx_ptr, self._win_ptr, self._img_ptr, 0, 0,
        )
        # ── Menu image (blitted only on change) ──────────────────────
        if self._needs_menu_redraw:
            md = self._menu_img_data
            mw = self._menu_w
            msl = self._menu_img_sl
            # Fill menu background
            self._fill_rect(0, 0, mw, self._win_h, *_MENU_BG,
                            img_data=md, img_w=mw, img_sl=msl)
            # Separator line (left edge of menu)
            self._draw_vline(0, 0, self._win_h - 1, 100, 100, 100,
                             img_data=md, img_w=mw, img_sl=msl)
            # Separator under speed row
            self._draw_hline(4, 216, 56, 60, 60, 60,
                             img_data=md, img_w=mw, img_sl=msl)
            # Blit menu image at the right side of the window
            mlx.mlx_put_image_to_window(  # type: ignore[union-attr]
                self._mlx_ptr, self._win_ptr, self._menu_img_ptr,
                self._maze_w, 0,
            )
            # Draw text on top of the menu image
            self._draw_menu_text()
            self._needs_menu_redraw = False

    def _draw_menu_text(self) -> None:
        """Draw the side-panel text using mlx_string_put."""
        m = self._mlx
        mp = self._mlx_ptr
        wp = self._win_ptr
        x: int = self._maze_w + 8

        # Title
        if self._game_mode:
            title, tc = "PLAY MODE", _rgb_to_color(*_GAME_COLOR)
        elif self._is_animating:
            title, tc = "BUILDING...", _rgb_to_color(*_ANIM_COLOR)
        else:
            title, tc = "A-Maze-ing", _rgb_to_color(*_MENU_HL)
        m.mlx_string_put(mp, wp, x, 16, tc, title)  # type: ignore[union-attr]

        # Speed indicator
        sc = _rgb_to_color(*(_ANIM_COLOR if self._is_animating else _MENU_FG))
        m.mlx_string_put(  # type: ignore[union-attr]
            mp, wp, x, 40, sc, f"+/- Speed: {self.anim_speed} step/fr",
        )

        # Menu items
        algo_short: str = self.current_algo[:20]
        shape_short: str = self.current_shape[:15]
        items = [
            "1/R  Re-generate",
            f"2    {algo_short}",
            f"3    {shape_short}",
            "4/P  Show/Hide path",
            "5/C  Rotate colors",
            f"G    Game: {'ON' if self._game_mode else 'OFF'}",
            "Q    Quit",
        ]
        start_y, item_h = 80, 34
        for i, label in enumerate(items):
            if self._game_mode and i == 5:
                col = _rgb_to_color(*_GAME_COLOR)
            elif self._is_animating and i < 3:
                col = _rgb_to_color(*_ANIM_COLOR)
            else:
                col = _rgb_to_color(*_MENU_FG)
            m.mlx_string_put(  # type: ignore[union-attr]
                mp, wp, x, start_y + i * item_h + 14, col, label,
            )

        # Play-mode stats
        if self._game_mode:
            sep_y: int = start_y + len(items) * item_h + 6
            # Draw separator line into the already-blitted image area
            steps_label: str = f"Steps: {self._player_steps}"
            steps_c = _rgb_to_color(
                *(_WIN_COLOR if self._game_won else _GAME_COLOR)
            )
            m.mlx_string_put(  # type: ignore[union-attr]
                mp, wp, x, sep_y + 18, steps_c, steps_label,
            )
            if self._game_won:
                m.mlx_string_put(  # type: ignore[union-attr]
                    mp, wp, x, sep_y + 38,
                    _rgb_to_color(*_WIN_COLOR), "*** YOU WIN! ***",
                )
                m.mlx_string_put(  # type: ignore[union-attr]
                    mp, wp, x, sep_y + 58,
                    _rgb_to_color(*_MENU_FG), "Press G to play again",
                )
            else:
                m.mlx_string_put(  # type: ignore[union-attr]
                    mp, wp, x, sep_y + 38,
                    _rgb_to_color(*_MENU_FG), "Arrows: navigate",
                )

    # ── Maze drawing ─────────────────────────────────────────────────────

    def _draw_maze(self) -> None:
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
                    self._fill_rect(
                        x + 1, y + 1, cs - 1, cs - 1, *_BLOCKED_COLOR,
                    )
                elif self._game_mode and (r, c) == self._player_pos:
                    col = _WIN_COLOR if self._game_won else _PLAYER_COLOR
                    self._fill_rect(x + 2, y + 2, cs - 3, cs - 3, *col)
                elif (r, c) in (self.entry, self.exit_cell):
                    self._fill_rect(
                        x + 1, y + 1, cs - 1, cs - 1, *self.path_color,
                    )
                elif self.show_solution and (r, c) in self.solution_cells:
                    self._fill_rect(
                        x + 1, y + 1, cs - 1, cs - 1, *self.solution_color,
                    )

                # Walls
                if cell & (1 << NORTH):
                    self._draw_hline(x, x + cs, y, *self.wall_color)
                if cell & (1 << EAST):
                    self._draw_vline(x + cs, y, y + cs, *self.wall_color)
                if cell & (1 << SOUTH):
                    self._draw_hline(x, x + cs, y + cs, *self.wall_color)
                if cell & (1 << WEST):
                    self._draw_vline(x, y, y + cs, *self.wall_color)
