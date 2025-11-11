.PHONY: test

VENV_PATH := .venv
PYTHON := $(VENV_PATH)/bin/python
PYTEST := $(PYTHON) -m pytest

test:
	$(PYTEST)
