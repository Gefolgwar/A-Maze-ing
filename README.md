<<<<<<< HEAD
# A-Maze-ing
=======
# *A-Maze-Ing*

> A Python maze generation, solving, and visualization project.

## Description

**A-Maze-Ing** generates perfect or imperfect mazes using a Recursive Backtracker algorithm, embeds the iconic **"42"** pattern as blocked cells, solves the maze with BFS, and outputs the result in a hex-encoded format. The project ships with both a terminal (ASCII) and a graphical (pygame) user interface.

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 2. Install
make install

# 3. Run
make run
```

## Project Structure

| Path | Owner | Description |
|------|-------|-------------|
| `src/mazegen/` | Dev A | Core generation library (packaged as `.whl`) |
| `solver/` | Dev B | BFS pathfinder |
| `ui/` | Dev B | Terminal (ASCII) and graphical (pygame) renderers |
| `a_maze_ing.py` | Dev B | CLI entry point |
| `config.txt` | Dev B | Runtime configuration (`KEY=VALUE`) |
| `settings.ini` | Dev B | UI colour/theme settings |
| `tests/` | Joint | Unit tests for generator logic and I/O |

## Configuration

### `config.txt` (required)

```
WIDTH=20
HEIGHT=15
SEED=42
PERFECT=True
ENTRY=0,0
EXIT=19,14
OUTPUT_FILE=output_maze.txt
```

### `settings.ini` (optional)

```ini
[UI]
WallColor=#FFFFFF
PathColor=#00FF00
SolutionColor=#FF0000
BackgroundColor=#000000
DisplayMode=terminal
CellSize=20
```

Set `DisplayMode=graphical` to launch the pygame window.

## Output Format

The output file contains:

1. **Hex rows** — one character per cell (0–F), encoding open directions as bits: N=0, E=1, S=2, W=3.
2. An **empty line**.
3. **Entry** and **Exit** coordinates.
4. The **Solution** path as space-separated directions (`N E S W`).

## Hex Encoding

Each cell is a 4-bit value:

| Bit | Direction | Value |
|-----|-----------|-------|
| 0   | North     | 1     |
| 1   | East      | 2     |
| 2   | South     | 4     |
| 3   | West      | 8     |

A set bit means the wall is **closed** (present). For example, `0x3` = `0011` = North and East walls closed, South and West open. `0xA` = `1010` = East and West walls closed.

## Makefile Targets

| Target | Action |
|--------|--------|
| `make install` | Install dependencies and package in editable mode |
| `make run` | Run `a_maze_ing.py config.txt` |
| `make lint` | Run flake8 + mypy |
| `make test` | Run pytest |
| `make debug` | Quick generator debug render in terminal |
| `make clean` | Remove build/cache artifacts |
| `make build` | Build `.whl` package via `python -m build` |

## Team Roles

- **Developer A (Algorithm Engineer):** Core `mazegen` package — generation algorithm, hex encoding, "42" pattern, 3×3 validation, wall coherency, and `debug_render()` stub.
- **Developer B (System/Integration Engineer):** CLI entry point, config parsing, BFS solver, terminal and graphical UIs, output file writing, `MockGenerator` stub, and this README.

## AI Usage

This project was developed with assistance from an AI coding assistant (Antigravity / Gemini). The AI helped with:

- Architecture planning and file structure
- Implementation of the Recursive Backtracker algorithm
- BFS solver logic
- Hex bitwise encoding and wall-coherency validation
- Terminal and pygame rendering code
- Test scaffolding and Makefile targets

All generated code was reviewed and integrated by the development team.

## License

MIT
>>>>>>> fde0c09 (Initial commit: basic project structure)
