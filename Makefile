# Python Code Style
reformat:
	black -l 99 --target-version py37 `git ls-files "*.py"`
stylecheck:
	black --check -l 99 --target-version py37 `git ls-files "*.py"`

# Translations
gettext:
	redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
upload_translations:
	$(MAKE) gettext
	crowdin upload sources
download_translations:
	crowdin download
