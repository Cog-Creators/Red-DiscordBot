reformat:
	black -l 99 `git ls-files "*.py"`
stylecheck:
	black -l 99 --check `git ls-files "*.py"`
