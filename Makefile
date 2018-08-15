reformat:
	black -l 99 `git ls-files "*.py"`
stylecheck:
	black --check -l 99 `git ls-files "*.py"`
gettext:
	redgettext --command-docstrings --verbose --recursive redbot
	crowdin upload
