PYTHON ?= python3.8

# Python Code Style
reformat:
	$(PYTHON) -m black `git ls-files "*.py"`
stylecheck:
	$(PYTHON) -m black --check `git ls-files "*.py"`
stylediff:
	$(PYTHON) -m black --check --diff `git ls-files "*.py"`

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
