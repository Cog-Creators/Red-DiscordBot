reformat:
	black -l 99 redbot tests setup.py generate_strings.py docs/conf.py
stylecheck:
	black --check -l 99 redbot tests setup.py generate_strings.py docs/conf.py
