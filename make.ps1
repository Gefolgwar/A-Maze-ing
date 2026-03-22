#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Windows PowerShell wrapper for the project Makefile targets.
.USAGE
    .\make.ps1 [target]
    Available targets: install, run, lint, test, debug, clean, build
#>

$PY = "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe"

$target = if ($args.Count -gt 0) { $args[0] } else { "run" }

switch ($target) {
    "install" {
        & pip install -r requirements.txt
        & pip install -e .
    }
    "run" {
        & $PY a_maze_ing.py config.txt
    }
    "lint" {
        & $PY -m flake8 --max-line-length 99 src/ solver/ ui/ a_maze_ing.py tests/
        & $PY -m mypy --ignore-missing-imports src/ a_maze_ing.py solver/ ui/
    }
    "test" {
        & $PY -m pytest tests/ -v
    }
    "debug" {
        & $PY -c "from mazegen import MazeGenerator; m = MazeGenerator(20, 15, 42); m.debug_render(); print(); m.debug_render_walls()"
    }
    "clean" {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, "*.egg-info", `
            "src/*.egg-info", __pycache__, "src/mazegen/__pycache__", `
            "solver/__pycache__", "ui/__pycache__", "tests/__pycache__", `
            ".mypy_cache", ".pytest_cache", "output_maze.txt"
    }
    "build" {
        & $PY -m build
    }
    default {
        Write-Host "Unknown target: $target"
        Write-Host "Available: install, run, lint, test, debug, clean, build"
        exit 1
    }
}
