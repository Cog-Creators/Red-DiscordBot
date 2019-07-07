# Python Code Style
reformat:
	black -l 99 `git ls-files "*.py"`
stylecheck:
	black --check -l 99 `git ls-files "*.py"`

# Translations
gettext:
	redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
upload_translations: gettext _crowdin_upload
# We need to make gettext before downloading because crowdin CLI uses existing `.pot` files to know
# where to extract the `.po` files.
download_translations: gettext _crowdin_download
_crowdin_upload:
	crowdin upload sources
_crowdin_download:
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
