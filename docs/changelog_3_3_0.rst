.. 3.3.x Changelogs

Redbot 3.3.6 (2020-04-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`yamikaitou`

End-user changelog
------------------

Core Bot
********

- Converting from and to Postgres driver with ``redbot-setup convert`` have been fixed (:issue:`3714`, :issue:`3115`)
- Fixed big delays in commands that happened when the bot was owner-less (or if it only used co-owners feature) and command caller wasn't the owner (:issue:`3782`)
- Various optimizations

  - Reduced calls to data backend when loading bot's commands (:issue:`3764`)
  - Reduced calls to data backend when showing help for cogs/commands (:issue:`3766`)
  - Improved performance for bots with big amount of guilds (:issue:`3767`)
  - Mod cog no longer fetches guild's bans every 60 seconds when handling unbanning for tempbans (:issue:`3783`)
  - Reduced the bot load for messages starting with a prefix when fuzzy search is disabled (:issue:`3718`)
  - Aliases in Alias cog are now cached for better performance (:issue:`3788`)

Core Commands
*************

- ``[p]set avatar`` now supports setting avatar using attachment (:issue:`3747`)
- Added ``[p]set avatar remove`` subcommand for removing bot's avatar (:issue:`3757`)
- Fixed list of ignored channels that is shown in ``[p]ignore``/``[p]unignore`` (:issue:`3746`)

Audio
*****

- Age-restricted tracks, live streams, and mix playlists from YouTube should work in Audio again (:issue:`3791`)
- Soundcloud's sets and playlists with more than 50 tracks should work in Audio again (:issue:`3791`)

CustomCommands
**************

- Added ``[p]cc raw`` command that gives you the raw response of a custom command for ease of copy pasting (:issue:`3795`)

Modlog
******

- Fixed ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3784`, :issue:`3778`)

Streams
*******

- Fixed incorrect stream URLs for Twitch channels that have localised display name (:issue:`3773`, :issue:`3772`)

Trivia
******

- Fixed the error in ``[p]trivia stop`` that happened when there was no ongoing trivia session in the channel (:issue:`3774`)

Trivia Lists
************

- Updated ``leagueoflegends`` list with new changes to League of Legends (`b8ac70e <https://github.com/Cog-Creators/Red-DiscordBot/commit/b8ac70e59aa1328f246784f14f992d6ffe00d778>`_)


Developer changelog
-------------------

Utility Functions
*****************

- Added `redbot.core.utils.AsyncIter` utility class which allows you to wrap regular iterable into async iterator yielding items and sleeping for ``delay`` seconds every ``steps`` items (:issue:`3767`, :issue:`3776`)
- `bold()`, `italics()`, `strikethrough()`, and `underline()` now accept ``escape_formatting`` argument that can be used to disable escaping of markdown formatting in passed text (:issue:`3742`)


Documentation changes
---------------------

- Added `document about updating Red <update_red>` (:issue:`3790`)
- ``pyenv`` instructions will now update ``pyenv`` if it's already installed (:issue:`3740`)
- Updated Python version in ``pyenv`` instructions (:issue:`3740`)
- Updated install docs to include Ubuntu 20.04 (:issue:`3792`)


Miscellaneous
-------------

- **Config** - JSON driver will now properly have only one lock per cog name (:issue:`3780`)
- **Core Commands** - ``[p]debuginfo`` now shows used storage type (:issue:`3794`)
- **Trivia** - Corrected spelling of Compact Disc in ``games`` list (:issue:`3759`, :issue:`3758`)


Redbot 3.3.5 (2020-04-09)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`

End-user changelog
------------------

Core Bot
********

- "Outdated" field no longer shows in ``[p]info`` when Red is up-to-date (:issue:`3730`)

Alias
*****

- Fixed regression in ``[p]alias add`` that caused it to reject commands containing arguments (:issue:`3734`)


Redbot 3.3.4 (2020-04-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`kennnyshiwa`

End-user changelog
------------------

Core Bot
********

- Fixed checks related to bank's global state that were used in commands in Bank, Economy and Trivia cogs (:issue:`3707`)

Alias
*****

- ``[p]alias add`` now sends an error when command user tries to alias doesn't exist (:issue:`3710`, :issue:`3545`)

Developer changelog
-------------------

Core Bot
********

- Bump dependencies, including update to discord.py 1.3.3 (:issue:`3723`)

Utility Functions
*****************

- `redbot.core.utils.common_filters.filter_invites` now filters ``discord.io/discord.li`` invites links (:issue:`3717`)
- Fixed false-positives in `redbot.core.utils.common_filters.filter_invites` (:issue:`3717`)

Documentation changes
---------------------

- Versions of pre-requirements are now included in Windows install guide (:issue:`3708`)


Redbot 3.3.3 (2020-03-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`AnonGuy`, :ghuser:`Dav-Git`, :ghuser:`FancyJesse`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Core Bot
********

- Delete delay for command messages has been moved from Mod cog to Core (:issue:`3638`, :issue:`3636`)
- Fixed various bugs with blacklist and whitelist (:issue:`3643`, :issue:`3642`)
- Added ``[p]set regionalformat`` command that allows users to set regional formatting that is different from bot's locale (:issue:`3677`, :issue:`3588`)
- ``[p]set locale`` allows any valid locale now, not just locales for which Red has translations (:issue:`3676`, :issue:`3596`)
- Permissions for commands in Bank, Economy and Trivia cogs can now be overriden by Permissions cog (:issue:`3672`, :issue:`3233`)
- Outages of ``pypi.org`` no longer prevent the bot from starting (:issue:`3663`)
- Fixed formatting of help strings in fuzzy search results (:issue:`3673`, :issue:`3507`)
- Fixed few deprecation warnings related to menus and uvloop (:issue:`3644`, :issue:`3700`)

Core Commands
*************

- ``[p]set game`` no longer errors when trying to clear the status (:issue:`3630`, :issue:`3628`)
- All owner notifcations in Core now use proper prefixes in messages (:issue:`3632`)
- Added ``[p]set playing`` and ``[p]set streaming`` aliases for respectively ``[p]set game`` and ``[p]set stream`` (:issue:`3646`, :issue:`3590`)

ModLog
******

- Modlog's cases now keep last known username to prevent losing that information from case's message on edit (:issue:`3674`, :issue:`3443`)

CustomCom
*********

- Added ``[p]cc search`` command that allows users to search through created custom commands (:issue:`2573`)

Cleanup
*******

- Added ``[p]cleanup spam`` command that deletes duplicate messages from the last X messages and keeps only one copy (:issue:`3688`)
- Removed regex support in ``[p]cleanup self`` (:issue:`3704`)

Downloader
**********

- ``[p]cog checkforupdates`` now includes information about cogs that can't be installed due to Red/Python version requirements (:issue:`3678`, :issue:`3448`)

General
*******

- Added more detailed mode to ``[p]serverinfo`` command that can be accessed with ``[p]serverinfo 1`` (:issue:`2382`, :issue:`3659`)

Image
*****

- Users can now specify how many images should be returned in ``[p]imgur search`` and ``[p]imgur subreddit`` using ``[count]`` argument (:issue:`3667`, :issue:`3044`)
- ``[p]imgur search`` and ``[p]imgur subreddit`` now return one image by default (:issue:`3667`, :issue:`3044`)

Mod
***

- ``[p]userinfo`` now shows user's activities (:issue:`3669`)
- ``[p]userinfo`` now shows status icon near the username (:issue:`3669`)
- Muting no longer fails if user leaves while applying overwrite (:issue:`3627`)
- Fixed error that happened when Mod cog was loaded for the first time during bot startup (:issue:`3632`, :issue:`3626`)

Permissions
***********

- Commands for setting default rules now error when user tries to deny access to command designated as being always available (:issue:`3504`, :issue:`3465`)

Streams
*******

- Fixed an error that happened when no game was set on Twitch stream (:issue:`3631`)
- Preview picture for YouTube stream alerts is now bigger (:issue:`3689`, :issue:`3685`)
- YouTube channels with a livestream that doesn't have any current viewer are now properly showing as streaming (:issue:`3690`)
- Failures in Twitch API authentication are now logged (:issue:`3657`)

Trivia
******

- Added ``[p]triviaset custom upload/delete/list`` commands for managing custom trivia lists from Discord (:issue:`3420`, :issue:`3307`)
- Trivia sessions no longer error on payout when winner's balance would exceed max balance (:issue:`3666`, :issue:`3584`)

Warnings
********

- Sending warnings to warned user can now be disabled with ``[p]warnset toggledm`` command (:issue:`2929`, :issue:`2800`)
- Added ``[p]warnset warnchannel`` command that allows to set a channel where warnings should be sent to instead of the channel command was called in (:issue:`2929`, :issue:`2800`)
- Added ``[p]warnset togglechannel`` command that allows to disable sending warn message in guild channel (:issue:`2929`, :issue:`2800`)
- ``[p]warn`` now tells the moderator when bot wasn't able to send the warning to the user (:issue:`3653`, :issue:`3633`)


Developer changelog
-------------------

Core Bot
********

- Deprecation warnings issued by Red now use correct stack level so that the cog developers can find the cause of them (:issue:`3644`)

Dev Cog
*******

- Add ``__name__`` to environment's globals (:issue:`3649`, :issue:`3648`)


Documentation changes
---------------------

- Fixed install instructions for Mac in `install_linux_mac` (:issue:`3675`, :issue:`3436`)
- Windows install instructions now use ``choco upgrade`` commands instead of ``choco install`` to ensure up-to-date packages (:issue:`3684`)


Miscellaneous
-------------

- **Core Bot** - Command errors (i.e. command on cooldown, dm-only and guild-only commands, etc) can now be translated (:issue:`3665`, :issue:`2988`)
- **Core Bot** - ``redbot-setup`` now prints link to Getting started guide at the end of the setup (:issue:`3027`)
- **Core Bot** - Whitelist and blacklist commands now properly require passing at least one user (or role in case of local whitelist/blacklist) (:issue:`3652`, :issue:`3645`)
- **Downloader** - Fix misleading error appearing when repo name is already taken in ``[p]repo add`` (:issue:`3695`)
- **Downloader** - Improved error messages for unexpected errors in ``[p]repo add`` (:issue:`3656`)
- **Downloader** - Prevent encoding errors from crashing ``[p]cog update`` (:issue:`3639`, :issue:`3637`)
- **Trivia** - Non-finite numbers can no longer be passed to ``[p]triviaset timelimit``, ``[p]triviaset stopafter`` and ``[p]triviaset payout`` (:issue:`3668`, :issue:`3583`)
- **Utility Functions** - `redbot.core.utils.menus.menu()` now checks permissions *before* trying to clear reactions (:issue:`3589`, :issue:`3145`)


Redbot 3.3.2 (2020-02-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`chasehult`, :ghuser:`Dav-Git`, :ghuser:`DiscordLiz`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Hedlund01`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`trundleroo`, :ghuser:`TrustyJAID`, :ghuser:`zephyrkul`

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
- Fix a bug with ``[p]blacklist add`` that made it impossible to blacklist users that bot doesn't share a server with (:issue:`3472`, :issue:`3220`)
- Improve user experience of ``[p]set game/listening/watching/`` commands (:issue:`3562`)
- Add ``[p]licenceinfo`` alias for ``[p]licenseinfo`` command to conform with non-American English (:issue:`3460`)

Admin
*****

- ``[p]announce`` will now only send error message if an actual errors occurs (:issue:`3514`, :issue:`3513`)

Alias
*****

- ``[p]alias help`` will now properly work in non-English locales (:issue:`3546`)

Audio
*****

- Users should be able to play age-restricted tracks from YouTube again (:issue:`3620`)

Economy
*******

- Next payday time will now be adjusted for users when payday time is changed (:issue:`3496`, :issue:`3438`)

Downloader
**********

- Downloader will no longer fail because of invalid ``info.json`` files (:issue:`3533`, :issue:`3456`)
- Add better logging of errors when Downloader fails to add a repo (:issue:`3558`)

Image
*****

- Fix load error for users that updated Red from version lower than 3.1 to version 3.2 or newer (:issue:`3617`)

Mod
***

- ``[p]hackban`` and ``[p]unban`` commands support user mentions now (:issue:`3524`)
- Ignored guilds/channels have been moved from Mod cog to Core (:issue:`3472`)

Streams
*******

- Fix stream alerts for Twitch (:issue:`3487`)
- Significantly reduce the quota usage for YouTube stream alerts (:issue:`3237`)
- Add ``[p]streamset timer`` command which can be used to control how often the cog checks for live streams (:issue:`3237`)

Trivia
******

- Add better handling for errors in trivia session (:issue:`3606`)

Trivia Lists
************

- Remove empty answers in trivia lists (:issue:`3581`)

Warnings
********

- Users can now pass a reason to ``[p]unwarn`` command (:issue:`3490`, :issue:`3093`)


Developer changelog
-------------------

Core Bot
********

- Updated all our dependencies - we're using discord.py 1.3.2 now (:issue:`3609`)
- Add traceback logging to task exception handling (:issue:`3517`)
- Developers can now create a command from an async function wrapped in `functools.partial` (:issue:`3542`)
- Bot will now show deprecation warnings in logs (:issue:`3527`, :issue:`3615`)
- Subcommands of command group with ``invoke_without_command=True`` will again inherit this group's checks (:issue:`3614`)

Config
******

- Fix Config's singletons (:issue:`3137`, :issue:`3136`)

Utility Functions
*****************

- Add clearer error when page is of a wrong type in `redbot.core.utils.menus.menu()` (:issue:`3571`)

Dev Cog
*******

- Allow for top-level `await`, `async for` and `async with` in ``[p]debug`` and ``[p]repl`` commands (:issue:`3508`)

Downloader
**********

- Downloader will now replace ``[p]`` with clean prefix same as it does in help command (:issue:`3592`)
- Add schema validation to ``info.json`` file processing - it should now be easier to notice any issues with those files (:issue:`3533`, :issue:`3442`)


Documentation changes
---------------------

- Add guidelines for Cog Creators in `guide_cog_creation` document (:issue:`3568`)
- Restructure virtual environment instructions to improve user experience (:issue:`3495`, :issue:`3411`, :issue:`3412`)
- Getting started guide now explain use of quotes for arguments with spaces (:issue:`3555`, :issue:`3111`)
- ``latest`` version of docs now displays a warning about possible differences from current stable release (:issue:`3570`)
- Make systemd guide clearer on obtaining username and python path (:issue:`3537`, :issue:`3462`)
- Indicate instructions for different venv types in systemd guide better (:issue:`3538`)
- Service file in `autostart_systemd` now also waits for network connection to be ready (:issue:`3549`)
- Hide alias of ``randomize_colour`` in docs (:issue:`3491`)
- Add separate headers for each event predicate class for better navigation (:issue:`3595`, :issue:`3164`)
- Improve wording of explanation for ``required_cogs`` key in `guide_publish_cogs` (:issue:`3520`)


Miscellaneous
-------------

- Use more reliant way of checking if command is bot owner only in ``[p]warnaction`` (Warnings cog) (:issue:`3516`, :issue:`3515`)
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
