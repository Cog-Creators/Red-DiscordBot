.. 3.3.x Changelogs

Redbot 3.3.1 (2020-02-05)
=========================


Core Bot
--------

- Add a cli flag for setting a max size of message cache
- Allow to edit prefix from command line using ``redbot --edit``.
- Some functions have been changed to no longer use deprecated asyncio functions

Core Commands
-------------

- The short help text for dm has been made more useful
- dm no longer allows owners to have the bot attempt to DM itself

Utils
-----

- Passing the event loop explicitly in utils is deprecated (Removal in 3.4)

Mod Cog
-------

- Hackban now works properly without being provided a number of days

Documentation Changes
---------------------

- Add `-e` flag to `journalctl` command in systemd guide so that it takes the user to the end of logs automatically.
- Added section to install docs for CentOS 8
- Improve usage of apt update in docs

Redbot 3.3.0 (2020-01-26)
=========================

Core Bot
--------

- The bot's description is now configurable.
- We now use discord.py 1.3.1, this comes with added teams support.
- The commands module has been slightly restructured to provide more useful data to developers.
- Help is now self consistent in the extra formatting used.

Core Commands
-------------

- Slowmode should no longer error on nonsensical time quantities.
- Embed use can be configured per channel as well.

Documentation
-------------

- We've made some small fixes to inaccurate instructions about installing with pyenv.
- Notes about deprecating in 3.3 have been altered to 3.4 to match the intended timeframe.

Admin
-----

- Gives feedback when adding or removing a role doesn't make sense.

Audio
-----

- Playlist finding is more intuitive.
- disconnect and repeat commands no longer interfere with eachother.

CustomCom
---------

- No longer errors when exiting an interactive menu.

Cleanup
-------

- A rare edge case involving messages which are deleted during cleanup and are the only message was fixed.

Downloader
----------

- Some user facing messages were improved.
- Downloader's initialization can no longer time out at startup.

General
-------

- Roll command will no longer attempt to roll obscenely large amounts.

Mod
---

- You can set a default amount of days to clean up when banning.
- Ban and hackban now use that default.
- Users can now optionally be DMed their ban reason.

Permissions
-----------

- Now has stronger enforcement of prioritizing botwide settings.