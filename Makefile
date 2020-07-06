PYTHON ?= python3.8

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# Python Code Style
reformat:
	$(PYTHON) -m black $(ROOT_DIR)
stylecheck:
	$(PYTHON) -m black --check $(ROOT_DIR)
stylediff:
	$(PYTHON) -m black --check --diff $(ROOT_DIR)

# Translations
gettext:
	$(PYTHON) -m redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
upload_translations:
	crowdin upload sources
download_translations:
	crowdin download

# Dependencies
bumpdeps:
	$(PYTHON) tools/bumpdeps.py

# Development environment
newenv:
	$(PYTHON) -m venv --clear .venv
	.venv/bin/pip install -U pip setuptools
	$(MAKE) syncenv
syncenv:
	.venv/bin/pip install -Ur ./tools/dev-requirements.txt
