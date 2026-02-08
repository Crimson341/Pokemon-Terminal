PYTHON ?= python3
VENV ?= .venv

PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
POKEMON := $(VENV)/bin/pokemon
PYTHON_VENV := $(VENV)/bin/python

.PHONY: setup test dry-run kitty-setup clean-venv

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .
	$(PIP) install pytest

test:
	@if [ ! -x "$(PYTEST)" ]; then $(MAKE) setup; fi
	$(PYTEST) -q

dry-run:
	@if [ ! -x "$(POKEMON)" ]; then $(MAKE) setup; fi
	$(POKEMON) -dr

kitty-setup:
	@if [ ! -x "$(PYTHON_VENV)" ]; then $(MAKE) setup; fi
	$(PYTHON_VENV) scripts/kitty_setup.py

clean-venv:
	rm -rf $(VENV)
