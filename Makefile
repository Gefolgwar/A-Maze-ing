PYTHON ?= .venv/bin/python3

.PHONY: install run lint debug clean build test

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

run:
	$(PYTHON) a_maze_ing.py config.txt

lint:
	flake8 --max-line-length 99 src/ solver/ ui/ a_maze_ing.py tests/
	mypy --ignore-missing-imports src/ a_maze_ing.py solver/ ui/

test:
	$(PYTHON) -m pytest tests/ -v

debug:
	$(PYTHON) -c "from mazegen import MazeGenerator; m = MazeGenerator(20, 15, 42); m.debug_render(); print(); m.debug_render_walls()"

clean:
	rm -rf build dist *.egg-info src/*.egg-info __pycache__ src/__pycache__
	rm -rf src/mazegen/__pycache__ solver/__pycache__ ui/__pycache__ tests/__pycache__
	rm -rf .mypy_cache .pytest_cache output_maze.txt

build:
	$(PYTHON) -m build
