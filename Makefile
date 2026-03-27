PYTHON ?= .venv/bin/python3

.PHONY: install run debug clean lint lint-strict

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

run:
	$(PYTHON) a_maze_ing.py config.txt

debug:
	$(PYTHON) -m pdb a_maze_ing.py config.txt

clean:
	rm -rf build dist *.egg-info src/*.egg-info __pycache__ src/__pycache__
	rm -rf src/mazegen/__pycache__ solver/__pycache__ ui/__pycache__ tests/__pycache__
	rm -rf .mypy_cache .pytest_cache output_maze.txt

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
