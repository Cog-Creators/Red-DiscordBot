# Python Code Style
reformat:
	black -l 99 `git ls-files "*.py"`
stylecheck:
	black --check -l 99 `git ls-files "*.py"`

# Translations
gettext:
	redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
upload_translations:
	$(MAKE) gettext
	crowdin upload sources
download_translations:
	crowdin download

# Dependencies
bumpdeps:
	python tools/bumpdeps.py

# Development environment
newenv:
	python3.7 -m venv --clear .venv
	.venv/bin/pip install -U pip setuptools
	$(MAKE) syncenv
syncenv:
	.venv/bin/pip install -Ur ./tools/dev-requirements.txt

# Changelog check
checkchangelog:
	bash tools/check_changelog_entries.sh
	python -m towncrier --draft
