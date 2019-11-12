PYTHON ?= python3.7

# Python Code Style
reformat:
	$(PYTHON) -m isort `git ls-files "*.py"`
	$(PYTHON) -m black -l 99 --target-version py37 `git ls-files "*.py"`
stylecheck:
	$(PYTHON) -m isort --check-only `git ls-files "*.py"`
	$(PYTHON) -m black --check -l 99 --target-version py37 `git ls-files "*.py"`

# Translations
gettext:
	$(PYTHON) -m redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
upload_translations:
	$(MAKE) gettext
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

# Changelog check
checkchangelog:
	bash tools/check_changelog_entries.sh
	$(PYTHON) -m towncrier --draft
