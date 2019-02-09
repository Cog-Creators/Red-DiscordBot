reformat:
	black -l 99 -N `git ls-files "*.py"`
stylecheck:
	black --check -l 99 -N `git ls-files "*.py"`
gettext:
	redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
	crowdin upload

REF?=rewrite
update_vendor:
	pip install --upgrade --no-deps -t . https://github.com/Rapptz/discord.py/archive/$(REF).tar.gz#egg=discord.py
	rm -r discord.py*-info
	$(MAKE) reformat
