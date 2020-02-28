.. 3.3.x Changelogs

Redbot 3.3.2 (2020-02-28)
=========================

End-user changelog
------------------

Core Bot
********

- Ignored guilds/channels and whitelist/blacklist are now cached for performance (:issue:`3472`)
- Ignored guilds/channels have been moved from Mod cog to Core (:issue:`3472`)
- ``[p]ignore channel`` command can now also ignore channel categories (:issue:`3472`)

Core Commands
*************

- Core cogs will now send bot mention prefix properly in places where discord doesn't render mentions (:issue:`3579`, :issue:`3591`, :issue:`3499`)
- Improve user experience of ``[p]set game/listening/watching/`` commands (:issue:`3562`)
- Add ``[p]licenceinfo`` alias for ``[p]licenseinfo`` command to conform with non-American English (:issue:`3460`)

Admin
*****

- ``[p]announce`` will now only send error message if an actual errors occurs (:issue:`3514`, :issue:`3513`)

Alias
*****

- ``[p]alias help`` will now properly work in non-English locales (:issue:`3546`)

Economy
*******

- Changing payday time will now also change the time when users can use ``[p]payday`` next time

Downloader
**********

- Downloader will no longer fail because of invalid ``info.json`` files (:issue:`3533`, :issue:`3456`)
- Add better logging of errors when Downloader fails to add a repo (:issue:`3558`)

Image
*****

- Fix load error for users that updated from pre-3.1 releases to 3.2 or newer (:issue:`3617`)

Streams
*******

- Fix stream alerts for Twitch (:issue:`3487`)
- Significantly reduce the quota usage for YouTube stream alerts (:issue:`3237`)

Trivia
******

- Add better handling for errors in trivia session (:issue:`3606`)

Trivia Lists
************

- Remove empty answers in trivia lists (:issue:`3581`)

Warnings
********

- Users can now pass a reason to ``[p]unwarn`` command (:issue:`3490`)


Developer changelog
-------------------

Core Bot
********

- Updated all our dependencies - we're using discord.py 1.3.2 now (:issue:`3609`)
- Add traceback logging to task exception handling (:issue:`3517`)
- Developers can now create a command from `functools.partial` (:issue:`3542`)
- Bot will now show deprecation warnings in logs (:issue:`3527`)
- Subcommands of command group with ``invoke_without_command=True`` will again inherit this group's checks (:issue:`3614`)

Config
******

- Fix Config's singletons (:issue:`3137`, :issue:`3136`)

Utility Functions
*****************

- Add clearer error when page is of a wrong type in `redbot.core.utils.menus.menu()` (:issue:`3571`)

Downloader
**********

- Downloader will now replace ``[p]`` with clean prefix same as it does in help command (:issue:`3592`)
- Add schema validation to ``info.json`` file processing - any errors in the format of the file should be easier to notice now (:issue:`3533`, :issue:`3442`)


Documentation changes
---------------------

- Add guidelines for Cog Creators in `guide_cog_creation` document (:issue:`3568`)
- Restructure virtual environment instructions for better user experience (:issue:`3495`)
- Getting started guide now explain use of quotes for arguments with spaces (:issue:`3555`)
- ``latest`` version of docs now displays a warning about possible differences from current stable release (:issue:`3570`)
- Make systemd guide clearer on obtaining username and python path (:issue:`3537`)
- Indicate instructions for different venv types in systemd guide better (:issue:`3538`)
- Service file in `autostart_systemd` now also waits for network connection to be ready (:issue:`3549`)
- Hide alias of ``randomize_colour`` in docs (:issue:`3491`)
- Add separate headers for each event predicate class for better navigation (:issue:`3595`, :issue:`3164`)
- Improve wording of explanation for ``required_cogs`` key in `guide_publish_cogs` (:issue:`3520`)


Miscellaneous
-------------

- Use more reliant way of checking if command is bot owner only in ``[p]warnaction`` (:issue:`3516`)
- Update PyPI domain in ``[p]info`` and update checker (:issue:`3607`)
- Stop using deprecated code in core (:issue:`3610`)


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

- Add ``-e`` flag to ``journalctl`` command in systemd guide so that it takes the user to the end of logs automatically.
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