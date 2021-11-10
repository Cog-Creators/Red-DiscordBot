.. Red changelogs

Redbot 3.4.14 (2021-09-23)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`L33Tech`, :ghuser:`maxbooiii`, :ghuser:`RheingoldRiver`

Read before updating
--------------------

#. Versions of RHEL older than 8.4 (including 7) and versions of CentOS older than 8.4 (excluding 7) are no longer supported.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.14 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1239>`__.


End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added the new native Discord timestamp in the ``[p]uptime`` command (:issue:`5323`)

Enhancements
************

- **Core Bot** - ``redbot-setup delete`` command no longer requires database connection if the data deletion was not requested (:issue:`5312`, :issue:`5313`)

Fixes
*****

- **Audio** - Fixed intermittent 403 Forbidden errors (:issue:`5329`)
- **Modlog** - Fixed formatting of **Last modified at** field in Modlog cases (:issue:`5317`)


Documentation changes
---------------------

New Documentation
*****************

- Added install guide for CentOS Stream 8, Oracle Linux 8.4-8.x, and Rocky Linux 8 (:issue:`5328`)

Enhancements
************

- Each operating system now has a dedicated install guide (:issue:`5328`)
- Install guides for RHEL derivatives no longer require the use of pyenv (:issue:`5328`)

Fixes
*****

- Fixed Raspberry Pi OS install guide (:issue:`5314`, :issue:`5328`)


Redbot 3.4.13 (2021-09-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Arman0334`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`fredster33`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`qenu`, :ghuser:`TheDataLeek`, :ghuser:`Twentysix26`, :ghuser:`TwinDragon`, :ghuser:`Vexed01`

Read before updating
--------------------

#. If you're hosting a public/big bot (>75 servers) or strive to scale your bot at that level, you should read :doc:`our stance on (privileged) intents and public bots <intents>`.
#. Fedora 32 is no longer supported as it has already reached end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.13 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1238>`__.


End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added a new ``[p]diagnoseissues`` command to allow the bot owners to diagnose issues with various command checks with ease (:issue:`4717`, :issue:`5243`)

    Since some of us are pretty excited about this feature, here's a very small teaser showing a part of what it can do:

    .. figure:: https://user-images.githubusercontent.com/6032823/132610057-d6c65d67-c244-4f0b-9458-adfbe0c68cab.png

- **Core Bot** - Added a setting for ``[p]help``'s reaction timeout (:issue:`5205`)

    This can be changed with ``[p]helpset reacttimeout`` command

- **Core Bot** - Red 3.4.13 is the first release to (finally) support Python 3.9! (:issue:`4655`, :issue:`5121`)
- **Alias** - Added commands for editing existing aliases (:issue:`5108`)
- **Audio** - Added a per-guild max volume setting (:issue:`5165`)

    This can be changed with the ``[p]audioset maxvolume`` command

- **Cleanup** - All ``[p]cleanup`` commands will now send a notification with the number of deleted messages. The notification is deleted automatically after 5 seconds (:issue:`5218`)

    This can be disabled with the ``[p]cleanupset notify`` command

- **Filter** - Added ``[p]filter clear`` and ``[p]filter channel clear`` commands for clearing the server's/channel's filter list (:issue:`4841`, :issue:`4981`)

Enhancements
************

- **Core Bot** - Revamped the ``[p]debuginfo`` to make it more useful for... You guessed it, debugging! (:issue:`4997`, :issue:`5156`)

    More specifically, added information about CPU and RAM, bot's instance name and owners

- **Core Bot** - The formatting of Red's console logs has been updated to make it more copy-paste friendly (:issue:`4868`, :issue:`5181`)
- **Core Bot** - Added the new native Discord timestamps in Modlog cases, ``[p]userinfo``, ``[p]serverinfo``, and ``[p]tempban`` (:issue:`5155`, :issue:`5241`)
- **Core Bot** - Upgraded all Red's dependencies (:issue:`5121`)
- **Core Bot** - The console error about missing Privileged Intents stands out more now (:issue:`5184`)
- **Core Bot** - The ``[p]invite`` command will now add a tick reaction after it DMs an invite link to the user (:issue:`5184`)
- **Admin** - The ``[p]selfroleset add`` and ``[p]selfroleset remove`` commands can now be used to add multiple selfroles at once (:issue:`5237`, :issue:`5238`)
- **Audio** - ``[p]summon`` will now indicate that it has succeeded or failed to summon the bot (:issue:`5186`)
- **Cleanup** - The ``[p]cleanup user`` command can now be used to clean messages of a user that is no longer in the server (:issue:`5169`)
- **Downloader** - The dot character (``.``) can now be used in repo names. No more issues with adding repositories using the commands provided by the Cog Index! (:issue:`5214`)
- **Mod** - The DM message from the ``[p]tempban`` command will now include the ban reason if ``[p]modset dm`` setting is enabled (:issue:`4836`, :issue:`4837`)
- **Streams** - Made small optimizations in regards to stream alerts (:issue:`4968`)
- **Trivia** - Added schema validation of the custom trivia files (:issue:`4571`, :issue:`4659`)

Removals
********

- **Core Bot** - Fedora 32 is no longer supported as it has already reached end of life (:issue:`5121`)

Fixes
*****

- **Core Bot** - Fixed a bunch of errors related to the missing permissions and channels/messages no longer existing (:issue:`5109`, :issue:`5163`, :issue:`5172`, :issue:`5191`)
- **Audio** - Fixed an issue with short clips being cutoff when auto-disconnect on queue end is enabled (:issue:`5158`, :issue:`5188`)
- **Audio** - Fixed fetching of age-restricted tracks (:issue:`5233`)
- **Audio** - Fixed searching of YT Music (:issue:`5233`)
- **Audio** - Fixed playback from SoundCloud (:issue:`5233`)
- **Downloader** - Added a few missing line breaks (:issue:`5185`, :issue:`5187`)
- **Mod** - Fixed an error with handling of temporary ban expirations while the guild is unavailable due to Discord outage (:issue:`5173`)
- **Mod** - The ``[p]rename`` command will no longer permit changing nicknames of members that are not lower in the role hierarchy than the command caller (:issue:`5187`, :issue:`5211`)
- **Streams** - Fixed an issue with some YouTube streamers getting removed from stream alerts after a while (:issue:`5195`, :issue:`5223`)
- **Warnings** - 0 point warnings are, once again, allowed. (:issue:`5177`, :issue:`5178`)


Developer changelog
-------------------

New Functionality
*****************

- Added `RelativedeltaConverter` and `parse_relativedelta` to the ``redbot.core.commands`` package (:issue:`5000`)

    This converter and function return `dateutil.relativedelta.relativedelta` object that represents a relative delta.
    In addition to regular timedelta arguments, it also accepts months and years!

- Added more APIs for allowlists and blocklists (:issue:`5206`)

    Here's the list of the methods that were added to the ``bot`` object:

        - `Red.add_to_blacklist()`
        - `Red.remove_from_blacklist()`
        - `Red.get_blacklist()`
        - `Red.clear_blacklist()`
        - `Red.add_to_whitelist()`
        - `Red.remove_from_whitelist()`
        - `Red.get_whitelist()`
        - `Red.clear_whitelist()`

- Added `CommandConverter` and `CogConverter` to the ``redbot.core.commands`` package (:issue:`5037`)


Documentation changes
---------------------

New Documentation
*****************

- Added a document about (privileged) intents and our stance regarding "public bots" (:issue:`5216`, :issue:`5221`)
- Added install instructions for Debian 11 Bullseye (:issue:`5213`, :issue:`5217`)
- Added Oracle Cloud's Always Free offering to the :ref:`host-list` (:issue:`5225`)

Enhancements
************

- Updated the commands in the install guide for Mac OS to work properly on Apple Silicon devices (:issue:`5234`)

Fixes
*****

- Fixed the examples of commands that are only available to people with the mod role (:issue:`5180`)
- Fixed few other small issues with the documentation :) (:issue:`5048`, :issue:`5092`, :issue:`5149`, :issue:`5207`, :issue:`5209`, :issue:`5215`, :issue:`5219`, :issue:`5220`)


Redbot 3.4.12 (2021-06-17)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`npc203`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Stonedestroyer`

This is a hotfix release related to Red ceasing to use the Audio Global API service.

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - ``applications.commands`` scope can now be included in the invite URL returned from ``[p]invite`` by enabling it with``[p]inviteset commandscope``

Enhancements
************

- **Core Bot** - ``[p]set serverprefix`` command will now prevent the user from setting a prefix with length greater than 20 characters (:issue:`5091`, :issue:`5117`)
- **Core Bot** - ``[p]set prefix`` command will now warn the user when trying to set a prefix with length greater than 20 characters (:issue:`5091`, :issue:`5117`)
- **Audio** - All local caches are now enabled by default (:issue:`5140`)
- **Dev Cog** - ``[p]debug`` command will now confirm the code finished running with a tick reaction (:issue:`5107`)

Removals
********

- **Audio** - Global API service will no longer be used in Audio and as such support for it has been removed from the cog (:issue:`5143`)

Fixes
*****

- **Audio** - Updated URL of the curated playlist (:issue:`5135`)
- **Filter** - Fixed an edge case that caused the cog to sometimes check contents of DM messages (:issue:`5125`)
- **Warnings** - Prevented users from applying 0 or less points in custom warning reasons (:issue:`5119`, :issue:`5120`)


Redbot 3.4.11 (2021-06-12)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Onii-Chan-Discord`

This is a hotfix release fixing a crash involving guild uploaded stickers.

End-user changelog
------------------

Enhancements
************

- discord.py version has been bumped to 1.7.3 (:issue:`5129`)

Fixes
*****

- Links to the CogBoard in Red's documentation have been updated to use the new domain (:issue:`5124`)


Redbot 3.4.10 (2021-05-28)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`benno1237`, :ghuser:`bobloy`, :ghuser:`BoyDownTown`, :ghuser:`Danstr5544`, :ghuser:`DeltaXWizard`, :ghuser:`Drapersniper`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Lifeismana`, :ghuser:`Obi-Wan3`, :ghuser:`OofChair`, :ghuser:`palmtree5`, :ghuser:`plofts`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`

Read before updating
--------------------

#. PM2 process manager is no longer supported as it is not a viable solution due to certain parts of its behavior.

    We highly recommend you to switch to one of the other supported solutions:
        - `autostart_systemd`
        - `autostart_mac`

    If you experience any issues when trying to configure it, you can join `our discord server <https://discord.gg/red>`__ and ask in the **support** channel for help.

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    - Red 3.4.10 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1233>`__.
    - We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.10/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.


End-user changelog
------------------

New Functionality
*****************

- **Streams** - In message template, ``{stream.display_name}`` can now be used to refer to streamer's display name (:issue:`5050`, :issue:`5066`)

    - This is not always the same as ``{stream}`` which refers to the streamer's channel or username

Enhancements
************

- Rephrased a few strings and fixed maaaaany grammar issues and typos (:issue:`4793`, :issue:`4832`, :issue:`4955`, :issue:`4966`, :issue:`5015`, :issue:`5019`, :issue:`5029`, :issue:`5038`, :issue:`5055`, :issue:`5080`, :issue:`5081`)
- **Admin** - The cog will now log when it leaves a guild due to the serverlock (:issue:`5008`, :issue:`5073`)
- **Audio** - The ``[p]audiostats`` command can now only be used by bot owners (:issue:`5017`)
- **Audio** - The cog will now check whether it has speak permissions in the channel before performing any actions (:issue:`5012`)
- **Audio** - Improved logging in Audio cog (:issue:`5044`)
- **Cleanup** - Clarified that ``[p]cleanup`` commands only delete the messages from the current channel (:issue:`5070`)
- **Downloader** - ``[p]repo remove`` can now remove multiple repos at the same time (:issue:`4765`, :issue:`5082`)
- **General** - The ``[p]urban`` command will now use the default embed color of the bot (:issue:`5014`)
- **Modlog** - Modlog will no longer try editing the case's Discord message once it knows that it no longer exists (:issue:`4975`)
- **Modlog** - ``[p]modlogset resetcases`` will now ask for confirmation before proceeding (:issue:`4976`)
- **Streams** - - Improved logging of API errors in Streams cog (:issue:`4995`)

Removals
********

- **Streams** - Smashcast service has been closed and for that reason we have removed support for it from the cog (:issue:`5039`, :issue:`5040`)

Fixes
*****

- **Core Bot** - Fixed terminal colors on Windows (:issue:`5063`)
- **Core Bot** - Fixed the ``--rich-traceback-extra-lines`` flag (:issue:`5028`)
- **Core Bot** - Added missing information about the ``showaliases`` setting in ``[p]helpset showsettings`` (:issue:`4971`)
- **Core Bot** - The help command no longer errors when it doesn't have permission to read message history and menus are enabled (:issue:`4959`, :issue:`5030`)
- **Core Bot** - Fixed a bug in ``[p]embedset user`` that made it impossible to reset the user's embed setting (:issue:`4962`)
- **Core Bot** - ``[p]embedset command`` and its subcommands now properly check whether any of the passed command's parents require Embed Links permission (:issue:`4962`)
- **Core Bot** - Fixed an issue with Red reloading unrelated modules when using ``[p]load`` and ``[p]reload`` (:issue:`4956`, :issue:`4958`)
- **Audio** - Fixed an issue that made it possible to remove Aikaterna's curated tracks playlist (:issue:`5018`)
- **Audio** - Fixed auto-resume of auto play after Lavalink restart (:issue:`5051`)
- **Audio** - Fixed an error with ``[p]audiostats`` caused by players not always having their connection time stored (:issue:`5046`)
- **Audio** - Fixed track resuming in a certain edge case (:issue:`4996`)
- **Audio** - Fixed an error in ``[p]audioset restart`` (:issue:`4987`)
- **Audio** - Fixed an issue with Audio failing when it's missing permissions to send a message in the notification channel (:issue:`4960`)
- **Audio** - Fixed fetching of age-restricted tracks (:issue:`5085`)
- **Audio** - Fixed an issue with Soundcloud URLs that ended with a slash (``/``) character (:issue:`5085`)
- **CustomCommands** - ``[p]customcom create simple`` no longer errors for a few specific names (:issue:`5026`, :issue:`5027`)
- **Downloader** - ``[p]cog install`` now properly shows the repo name rather than ``{repo.name}`` (:issue:`4954`)
- **Mod** - ``[p]mute`` no longer errors on muting a bot user if the ``senddm`` option is enabled (:issue:`5071`)
- **Mutes** - Forbidden errors during the channel mute are now handled properly in a rare edge case (:issue:`4994`)
- **Streams** - Fixed Picarto support (:issue:`4969`, :issue:`4970`)
- **Streams** - ``[p]twitchstream``, ``[p]youtubestream``, and ``[p]picarto`` commands can no longer be run in DMs (:issue:`5036`, :issue:`5035`)
- **Streams** - Fixed Twitch stream alerts for streams that use localized display names (:issue:`5050`, :issue:`5066`)
- **Streams** - The cog no longer errors when trying to delete a cached message from a channel that no longer exists (:issue:`5032`, :issue:`5031`)
- **Warnings** - The warn action is now taken *after* sending the warn message to the member (:issue:`4713`, :issue:`5004`)


Developer changelog
-------------------

Enhancements
************

- Bumped discord.py to 1.7.2 (:issue:`5066`)
- **Dev** - ``[p]eval``, ``[p]repl``, and ``[p]debug`` commands now, in addition to ``py``, support code blocks with ``python`` syntax (:issue:`5083`)

Fixes
*****

- The log messages shown by the global error handler will now show the trace properly for task done callbacks (:issue:`4980`)
- **Dev** - ``[p]eval``, ``[p]repl``, and ``[p]debug`` commands no longer fail to send very long syntax errors (:issue:`5041`)


Documentation changes
---------------------

New Documentation
*****************

- Added `a guide for making auto-restart service on Mac <autostart_mac>` (:issue:`4082`, :issue:`5020`)
- Added `cog guide for core commands <cog_guides/core>` (:issue:`1734`, :issue:`4597`)
- Added `cog guide for Mod cog <cog_guides/mod>` (:issue:`1734`, :issue:`4886`)
- Added `cog guide for Modlog cog <cog_guides/modlog>` (:issue:`1734`, :issue:`4919`)
- Added `cog guide for Mutes cog <cog_guides/mutes>` (:issue:`1734`, :issue:`4875`)
- Added `cog guide for Permissions cog <cog_guides/permissions>` (:issue:`1734`, :issue:`4985`)
- Added `cog guide for Reports cog <cog_guides/reports>` (:issue:`1734`, :issue:`4882`)
- Added `cog guide for Warnings cog <cog_guides/warnings>` (:issue:`1734`, :issue:`4920`)
- Added :ref:`a guide about Trivia list creation <guide_trivia_list_creation>` (:issue:`4595`, :issue:`5023`)
- Added the documentation for `redbot.core.modlog.Case` (:issue:`4979`)
- Added information on how to set the bot not to start on boot anymore to auto-restart docs (:issue:`5020`)

Enhancements
************

- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5025`)
- Cog creation guide now includes the ``bot`` as an argument to the cog class (:issue:`4988`)

Removals
********

- Removed PM2 guide (:issue:`4991`)


Redbot 3.4.9 (2021-04-06)
=========================

This is a hotfix release fixing an issue with command error handling.

discord.py version has been bumped to 1.7.1.

Thanks again to :ghuser:`Rapptz` for quick response on this issue.


Redbot 3.4.8 (2021-04-06)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`6days9weeks`, :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kingslayer268`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Obi-Wan3`, :ghuser:`OofChair`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`rijusougata13`, :ghuser:`TheDiscordHistorian`, :ghuser:`Tobotimus`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.8 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1212>`__.

#. Fedora 31 and OpenSUSE Leap 15.1 are no longer supported as they have already reached end of life.


End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added per-command embed settings (:issue:`4049`)

    - See help of ``[p]embedset`` and ``[p]embedset command`` command group for more information

- **Core Bot** - ``[p]leave`` accepts server IDs now (:issue:`4831`)
- **Core Bot** - An error message will now be shown when a command that is only available in NSFW channels is used in a non-NSFW channel (:issue:`4933`)
- **Trivia** - Added a new option for hiding the answer to the Trivia answer in a spoiler (:issue:`4700`, :issue:`4877`)

    - ``[p]triviaset usespoilers`` command can be used to enable/disable this option

Enhancements
************

- **Core Bot** - The ``[p]servers`` command uses menus now (:issue:`4720`, :issue:`4831`)
- **Core Bot** - Commands for listing global and local allowlists and blocklists will now, in addition to IDs, contain user/role names (:issue:`4839`)
- **Core Bot** - Added a progress bar to ``redbot-setup convert`` (:issue:`2952`)
- **Core Bot** - Added more singular and plural forms in a bunch of commands in the bot (:issue:`4004`, :issue:`4898`)
- **Audio** - Improved playlist extraction (:issue:`4932`)
- **Cleanup** - ``[p]cleanup before`` and ``[p]cleanup after`` commands can now be used without a message ID if the invocation message replies to some message (:issue:`4790`)
- **Filter** - Added meaningful error messages for incorrect arguments in the ``[p]bank set`` command (:issue:`4789`, :issue:`4801`)
- **Mod** - Improved performance of checking tempban expirations (:issue:`4907`)
- **Mutes** - Vastly improved performance of automatic unmute handling (:issue:`4906`)
- **Streams** - Streams cog should now load faster on bots that have many stream alerts set up (:issue:`4731`, :issue:`4742`)
- **Streams** - Checking Twitch streams will now make less API calls (:issue:`4938`)
- **Streams** - Ratelimits from Twitch API are now properly handled (:issue:`4808`, :issue:`4883`)
- **Warnings** - Embeds now use the default embed color of the bot (:issue:`4878`)

Removals
********

- **Core Bot** - Removed the option to drop the entire PostgreSQL database in ``redbot-setup delete`` due to limitations of PostgreSQL (:issue:`3699`, :issue:`3833`)

Fixes
*****

- **Core Bot** - Messages sent interactively in DM channels no longer fail (:issue:`4876`)
- **Core Bot** - Fixed how the command signature is shown in help for subcommands that have group args (:issue:`4928`)
- **Alias** - Fixed issues with command aliases for commands that take an arbitrary, but non-zero, number of arguments (e.g. ``[p]load``) (:issue:`4766`, :issue:`4871`)
- **Audio** - Fixed stuttering (:issue:`4565`)
- **Audio** - Fixed random disconnects (:issue:`4565`)
- **Audio** - Fixed the issues causing the player to be stuck on 00:00 (:issue:`4565`)
- **Audio** - Fixed ghost players (:issue:`4565`)
- **Audio** - Audio will no longer stop playing after a while (:issue:`4565`)
- **Audio** - Fixed playlist loading for playlists with over 100 songs (:issue:`4932`)
- **Audio** - Fixed an issue with alerts causing errors in playlists being loaded (:issue:`4932`)
- **Audio** - Fixed an issue with consent pages appearing while trying to load songs or playlists (:issue:`4932`)
- **Downloader** - Improved compatibility with Git 2.31 and newer (:issue:`4897`)
- **Mod** - Fixed tracking of nicknames that were set just before nick reset (:issue:`4830`)
- **Streams** - Fixed possible memory leak related to automatic message deletion (:issue:`4731`, :issue:`4742`)
- **Streams** - Streamer accounts that no longer exist are now properly handled (:issue:`4735`, :issue:`4746`)
- **Streams** - Fixed stream alerts being sent even after unloading Streams cog (:issue:`4940`)
- **Warnings** - Fixed output of ``[p]warnings`` command for members that are no longer in the server (:issue:`4900`, :issue:`4904`)


Developer changelog
-------------------

Enhancements
************

- Bumped discord.py version to 1.7.0 (:issue:`4928`)

Deprecations
************

- Deprecated importing ``GuildConverter`` from ``redbot.core.commands.converter`` namespace (:issue:`4928`)

    - ``discord.Guild`` or ``GuildConverter`` from ``redbot.core.commands`` should be used instead
- Added ``guild`` parameter to `bot.allowed_by_whitelist_blacklist() <Red.allowed_by_whitelist_blacklist()>` which is meant to replace the deprecated ``guild_id`` parameter (:issue:`4905`, :issue:`4914`)

    - Read the method's documentation for more information

Fixes
*****

- Fixed ``on_red_api_tokens_update`` not being dispatched when the tokens were removed with ``[p]set api remove`` (:issue:`4916`, :issue:`4917`)


Documentation changes
---------------------

New Documentation
*****************

- Added `cog guide for Image cog <cog_guides/image>` (:issue:`4821`)

Enhancements
************

- Added a note about updating cogs in update message and documentation (:issue:`4910`)
- `getting-started` now contains an explanation of parameters that can take an arbitrary number of arguments (:issue:`4888`, :issue:`4889`)
- All shell commands in the documentation are now prefixed with an unselectable prompt (:issue:`4908`)
- `systemd-service-guide` now asks the user to create the new service file using ``nano`` text editor (:issue:`4869`, :issue:`4870`)

    - Instructions for all Linux-based operating systems now recommend to install ``nano``
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`4864`, :issue:`4942`)
- Added a warning to Arch Linux install guide about the instructions being out-of-date (:issue:`4866`)

Fixes
*****

- Updated Mac install guide with new ``brew`` commands (:issue:`4865`)


Redbot 3.4.7 (2021-02-26)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`elijabesu`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`palmtree5`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Security
********

- Added proper permission checks to ``[p]muteset senddm`` and ``[p]muteset showmoderator`` (:issue:`4849`)

Enhancements
************

- Updated the ``[p]info`` command to more clearly indicate that the instance is owned by a team (:issue:`4851`)

Fixes
*****

- Updated the ``[p]lmgtfy`` command to use the new domain (:issue:`4840`)
- Fixed minor issues with error messages in Mutes cog (:issue:`4847`, :issue:`4850`, :issue:`4853`)

Documentation changes
---------------------

New Documentation
*****************

- Added `cog guide for General cog <cog_guides/general>` (:issue:`4797`)
- Added `cog guide for Trivia cog <cog_guides/trivia>` (:issue:`4566`)


Redbot 3.4.6 (2021-02-16)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`Andeeeee`, :ghuser:`bobloy`, :ghuser:`BreezeQS`, :ghuser:`Danstr5544`, :ghuser:`Dav-Git`, :ghuser:`Elysweyr`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`NeuroAssassin`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Strafee`, :ghuser:`TheWyn`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.6 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1199>`__.


End-user changelog
------------------

Security
********

- **Mutes** - Added more role hierarchy checks to ensure permission escalations cannot occur on servers with a careless configuration (:issue:`4741`)

New Functionality
*****************

- **Core Bot** - Help now includes command aliases in the command help (:issue:`3040`)

    - This can be disabled with ``[p]helpset showaliases`` command

- **Mod** - Added two new settings for disabling username and nickname tracking (:issue:`4799`)

    - Added a command ``[p]modset trackallnames`` that disables username tracking and overrides the nickname tracking setting for all guilds
    - Added a command ``[p]modset tracknicknames`` that disables nickname tracking in a specific guild
- **Mod** - Added a command ``[p]modset deletenames`` that deletes all stored usernames and nicknames (:issue:`4827`)
- **Modlog** - Added a command ``[p]listcases`` that allows you to see multiple cases for a user at once (:issue:`4426`)
- **Mutes** - A DM can now be sent to the (un)muted user on mute and unmute (:issue:`3752`, :issue:`4563`)

    - Added ``[p]muteset senddm`` to set whether the DM should be sent (function disabled by default)
    - Added ``[p]muteset showmoderator`` to set whether the DM sent to the user should include the name of the moderator that muted the user (function disabled by default)
- **Trivia Lists** - Added new Who's That Pokémon - Gen. VI trivia list (:issue:`4785`)

Enhancements
************

- Red's dependencies have been bumped (:issue:`4572`)
- **Core Bot** - Improvements and fixes for our new (colorful) logging (:issue:`4702`, :issue:`4726`)

    - The colors used have been adjusted to be readable on many more terminal applications
    - The ``NO_COLOR`` environment variable can now be set to forcefully disable all colors in the console output
    - Tracebacks will now use the full width of the terminal again
    - Tracebacks no longer contain multiple lines per stack level (this can now be changed with the flag ``--rich-traceback-extra-lines``)
    - Disabled syntax highlighting on the log messages
    - Dev cog no longer captures logging output
    - Added some cool features for developers

        - Added the flag ``--rich-traceback-extra-lines`` which can be used to set the number of additional lines in tracebacks
        - Added the flag ``--rich-traceback-show-locals`` which enables showing local variables in tracebacks

    - Improved and fixed a few other minor things
- **Core Bot** - Added a friendly error message to ``[p]load`` that is shown when trying to load a cog with a command name that is already taken by a different cog (:issue:`3870`)
- **Admin** - ``[p]selfrole`` can now be used without a subcommand and passed with a selfrole directly to add/remove it from the user running the command (:issue:`4826`)
- **Audio** - Improved detection of embed players for fallback on age-restricted YT tracks (:issue:`4818`, :issue:`4819`)
- **Audio** - Improved MP4/AAC decoding (:issue:`4818`, :issue:`4819`)
- **Audio** - Requests for YT tracks are now retried if the initial request causes a connection reset (:issue:`4818`, :issue:`4819`)
- **Cleanup** - Renamed the ``[p]cleanup spam`` command to ``[p]cleanup duplicates``, with the old name kept as an alias for the time being (:issue:`4814`)
- **Economy** - ``[p]economyset rolepaydayamount`` can now remove the previously set payday amount (:issue:`4661`, :issue:`4758`)
- **Filter** - Added a case type ``filterhit`` which is used to log filter hits (:issue:`4676`, :issue:`4739`)
- **Mod** - Added usage examples to ``[p]kick``, ``[p]ban``, ``[p]massban``, and ``[p]tempban`` (:issue:`4712`, :issue:`4715`)
- **Mod** - Updated DM on kick/ban to use bot's default embed color (:issue:`4822`)
- **Modlog** - Added typing indicator to ``[p]casesfor`` command (:issue:`4426`)
- **Reports** - Reports now use the default embed color of the bot (:issue:`4800`)
- **Trivia** - Payout for trivia sessions ending in a tie now gets split between all the players with the highest score (:issue:`3931`, :issue:`4649`)
- **Trivia Lists** - Updated answers regarding some of the hero's health and abilities in the ``overwatch`` trivia list (:issue:`4805`)

Fixes
*****

- Various grammar fixes (:issue:`4705`, :issue:`4748`, :issue:`4750`, :issue:`4763`, :issue:`4788`, :issue:`4792`, :issue:`4810`)
- **Core Bot** - Fixed the rotation of Red's logs that could before result in big disk usage (:issue:`4405`, :issue:`4738`)
- **Core Bot** - Fixed command usage in the help messages for few commands in Red (:issue:`4599`, :issue:`4733`)
- **Core Bot** - Fixed errors in ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands (:issue:`4767`, :issue:`4768`)
- **Core Bot** - ``[p]command listdisabled guild`` can no longer be run in DMs (:issue:`4771`, :issue:`4772`)
- **Core Bot** - Fixed errors appearing when using Ctrl+C to interrupt ``redbot --edit`` (:issue:`3777`, :issue:`4572`)
- **Cleanup** - Fixed an error from passing an overly large integer as a message ID to ``[p]cleanup after`` and ``[p]cleanup before`` (:issue:`4791`)
- **Dev Cog** - Help descriptions of the cog and its commands now get translated properly (:issue:`4815`)
- **Mod** - The ``[p]tempban`` command no longer errors out when trying to ban a user in a guild with the vanity url feature that doesn't have a vanity url set (:issue:`4714`)
- **Mod** - Fixed an edge case in role hierarchy checks (:issue:`4740`)
- **Mutes** - Fixed an edge case in role hierarchy checks (:issue:`4740`)
- **Mutes** - The modlog reason no longer contains leading whitespace when it's passed *after* the mute time (:issue:`4749`)
- **Mutes** - Help descriptions of the cog and its commands now get translated properly (:issue:`4815`)
- **Streams** - Fixed incorrect timezone offsets for some YouTube stream schedules (:issue:`4693`, :issue:`4694`)
- **Streams** - Fixed meaningless errors happening when the YouTube API key becomes invalid or when the YouTube quota is exceeded (:issue:`4745`)


Developer changelog
-------------------

New Functionality
*****************

- Added an event ``on_red_before_identify`` that is dispatched before IDENTIFYing a session (:issue:`4647`)
- **Utility Functions** - Added a function `redbot.core.utils.chat_formatting.spoiler()` that wraps the given text in a spoiler (:issue:`4754`)
- **Dev Cog** - Cogs can now add their own variables to the environment of ``[p]debug``, ``[p]eval``, and ``[p]repl`` commands (:issue:`4667`)

    - Variables can be added and removed from the environment of Dev cog using two new methods:

        - `bot.add_dev_env_value() <Red.add_dev_env_value()>`
        - `bot.remove_dev_env_value() <Red.remove_dev_env_value()>`

Enhancements
************

- Updated versions of the libraries used in Red: discord.py to 1.6.0, aiohttp to 3.7.3 (:issue:`4728`)


Documentation changes
---------------------

New Documentation
*****************

- Added `cog guide for Filter cog <cog_guides/filter>` (:issue:`4579`)

Enhancements
************

- Added information about the Red Index to `guide_publish_cogs` (:issue:`4778`)
- Restructured the host list (:issue:`4710`)
- Clarified how to use pm2 with ``pyenv virtualenv`` (:issue:`4709`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`4770`)

Fixes
*****

- Updated the pip command for Red with the postgres extra in Linux/macOS install guide to work on zsh shell (:issue:`4697`)


Redbot 3.4.5 (2020-12-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Injabie3`, :ghuser:`NeuroAssassin`

This is a hotfix release fixing an issue with Streams cog failing to load.

End-user changelog
------------------

Fixes
*****

- **Streams** - Fixed Streams failing to load and work properly (:issue:`4687`, :issue:`4688`)


Redbot 3.4.4 (2020-12-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreus7`, :ghuser:`NeuroAssassin`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.4 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.2_1170>`__.

#. Ubuntu 16.04 is no longer supported as it will soon reach its end of life and it is no longer viable for us to maintain support for it.

    While you might still be able to run Red on it, we will no longer put any resources into supporting it. If you're using Ubuntu 16.04, we highly recommend that you upgrade to the latest LTS version of Ubuntu.


End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Red's logging will now shine in your terminal more than ever (:issue:`4577`)
- **Dev** - Added new ``[p]bypasscooldown`` command that allows owners to bypass command cooldowns (:issue:`4440`)
- **Streams** - YouTube stream schedules are now announced before the stream (:issue:`4615`)

    - Alerts about YouTube stream schedules can be disabled with a new ``[p]streamset ignoreschedule`` command (:issue:`4615`)
- **Trivia Lists** - Added ``whosthatpokemon5`` trivia list containing Pokémon from the 5th generation (:issue:`4646`)
- **Trivia Lists** - Added ``geography`` trivia list (:issue:`4618`)

Enhancements
************

- **Core Bot** - Improved consistency of command usage in the help messages within all commands in Core Red (:issue:`4589`)
- **Core Bot** - Added a friendly error when the duration provided to commands that use the ``commands.TimedeltaConverter`` converter is out of the maximum bounds allowed by Python interpreter (:issue:`4019`, :issue:`4628`, :issue:`4630`)
- **Audio** - Added more friendly messages for 429 errors to let users know they have been temporarily banned from accessing the service instead of a generic Lavalink error (:issue:`4683`)
- **Audio** - Environment information will now be appended to Lavalink tracebacks in the spring.log (:issue:`4683`)
- **Cleanup** - ``[p]cleanup self`` will now delete the command message when the bot has permissions to do so (:issue:`4640`)
- **Economy** - ``[p]economyset slotmin`` and ``[p]economyset slotmax`` now warn when the new value will cause the slots command to not work (:issue:`4583`)
- **General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4678`)
- **Streams** - Improved error logging (:issue:`4680`)

Fixes
*****

- **Core Bot** - Fixed an error when removing path from a different operating system than the bot is currently running on with ``[p]removepath`` (:issue:`2609`, :issue:`4662`, :issue:`4466`)
- **Audio** - Fixed ``[p]llset java`` failing to set the Java executable path (:issue:`4621`, :issue:`4624`)
- **Audio** - Fixed Soundcloud playback (:issue:`4683`)
- **Audio** - Fixed YouTube age-restricted track playback (:issue:`4683`)
- **Mod** - ``[p]ban`` command will no longer error out when the given reason is too long (:issue:`4187`, :issue:`4189`)
- **Streams** - Scheduled YouTube streams now work properly with the cog (:issue:`3691`, :issue:`4615`)


Developer changelog
-------------------

New Functionality
*****************

- `get_audit_reason()` can now be passed a ``shorten`` keyword argument which will automatically shorten the returned audit reason to fit the max length allowed by Discord audit logs (:issue:`4189`)

Enhancements
************

- ``bot.remove_command()`` now returns the command object of the removed command as does the equivalent method from `discord.ext.commands.Bot` class (:issue:`4636`)


Documentation changes
---------------------

New Documentation
*****************

- Added `cog guide for Downloader cog <cog_guides/downloader>` (:issue:`4511`)
- Added `cog guide for Economy cog <cog_guides/economy>` (:issue:`4519`)
- Added `cog guide for Streams cog <cog_guides/streams>` (:issue:`4521`)
- Added `guide_cog_creators` document (:issue:`4637`)

Removals
********

- Removed install instructions for Ubuntu 16.04 (:issue:`4650`)


Redbot 3.4.3 (2020-11-16)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`KianBral`, :ghuser:`maxbooiii`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.3 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1132>`__.

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added ``[p]set competing`` command that allows users to set the bot's competing status (:issue:`4607`, :issue:`4609`)
- **Audio** - Added support for SoundCloud HLS streams (:issue:`4608`)

Enhancements
************

- **Audio** - Improved AAC audio handling (:issue:`4608`)
- **Trivia** - ``[p]triviaset custom upload`` now ensures that the filename is lowercase when uploading (:issue:`4594`)

Fixes
*****

- **Audio** - Volume changes on ARM systems running a 64 bit OS will now work again (:issue:`4608`)
- **Audio** - Fixed only 100 results being returned on a Youtube playlist (:issue:`4608`)
- **Audio** - Fixed YouTube VOD duration being set to unknown (:issue:`3885`, :issue:`4608`)
- **Audio** - Fixed some YouTube livestreams getting stuck (:issue:`4608`)
- **Audio** - Fixed internal Lavalink manager failing for Java with untypical version formats (:issue:`4608`)
- **Economy** - The ``[p]leaderboard`` command no longer fails in DMs when a global bank is used (:issue:`4569`)
- **Mod** - The ban reason is now properly set in the audit log and modlog when using the ``[p]massban`` command (:issue:`4575`)
- **Mod** - The ``[p]userinfo`` command now shows the new Competing activity (:issue:`4610`, :issue:`4611`)
- **Modlog** - The ``[p]case`` and ``[p]casesfor`` commands no longer fail when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)
- **Mutes** - Fixed automatic remuting on member join for indefinite mutes (:issue:`4568`)


Developer changelog
-------------------

Fixes
*****

- ``modlog.get_case()`` and methods using it no longer raise when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)

Documentation changes
---------------------

New Documentation
*****************

- Added `guide for Cog Manager UI <cogmanagerui>` (:issue:`4152`)
- Added `cog guide for CustomCommands cog <customcommands>` (:issue:`4490`)


Redbot 3.4.2 (2020-10-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.2 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1128>`__.

End-user changelog
------------------

Enhancements
************

- **Core Bot** - Added info about the metadata file to ``redbot --debuginfo`` (:issue:`4557`)
- **Audio** - Commands in ``[p]llset`` group can now be used in DMs (:issue:`4562`)
- **Streams** - Added error messages when exceeding the YouTube quota in the Streams cog (:issue:`4552`)
- **Streams** - Improved logging for unexpected errors in the Streams cog (:issue:`4552`)

Fixes
*****

- **Audio** - Fixed the ``[p]local search`` command (:issue:`4553`)
- **Audio** - Fixed random "Something broke when playing the track." errors for YouTube tracks (:issue:`4559`)
- **Mod** - Fixed ``[p]massban`` not working for banning members that are in the server (:issue:`4556`, :issue:`4555`)

Documentation changes
---------------------

New Documentation
*****************

- Added `cog guide for Cleanup cog <cleanup>` (:issue:`4488`)

Removals
********

- Removed multi-line commands from Linux install guides to avoid confusing readers (:issue:`4550`)


Redbot 3.4.1 (2020-10-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`absj30`, :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`chloecormier`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Generaleoley`, :ghuser:`hisztendahl`, :ghuser:`jack1142`, :ghuser:`KaiGucci`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`NeuroAssassin`, :ghuser:`nfitzen`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`PythonTryHard`, :ghuser:`SharkyTheKing`, :ghuser:`Stonedestroyer`, :ghuser:`thisisjvgrace`, :ghuser:`TrustyJAID`, :ghuser:`TurnrDev`, :ghuser:`Vexed01`, :ghuser:`Vuks69`, :ghuser:`xBlynd`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. This release fixes a security issue in Mod cog. See `Security changelog below <important-341-2>` for more information.
#. This Red update bumps discord.py to version 1.5.1, which explicitly requests Discord intents. Red requires all Privileged Intents to be enabled. More information can be found at :ref:`enabling-privileged-intents`.
#. Mutes functionality has been moved from the Mod cog to a new separate cog (Mutes) featuring timed and role-based mutes. If you were using it (or want to start now), you can load the new cog with ``[p]load mutes``. You can see the full `Removals changelog below <important-341-1>`.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

   We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.1/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.
   Please ensure that the WS port in Audio's settings (``[p]llset wsport``) is set to the port from the ``application.yml``.

End-user changelog
------------------

.. _important-341-2:

Security
********

**NOTE:** If you can't update immediately, we recommend globally disabling the affected command until you can.

- **Mod** - Fixed unauthorized privilege escalation exploit in ``[p]massban`` (also called ``[p]hackban``) command. Full security advisory `can be found on our GitHub <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-mp9m-g7qj-6vqr>`__.

New Functionality
*****************

- **Core Bot** - Locales and regional formats can now be set in individual guilds using ``[p]set locale`` and ``[p]set regionalformat`` (:issue:`3896`, :issue:`1970`)

    - Global locale and regional format setters have been renamed to ``[p]set globallocale`` and ``[p]set globalregionalformat``
- **Core Bot** - Added ``[p]set api list`` to list all currently set API services, without tokens (:issue:`4370`)
- **Core Bot** - Added ``[p]set api remove`` to remove API services, including tokens (:issue:`4370`)
- **Core Bot** - Added ``[p]helpset usetick``, toggling command message being ticked when help is sent to DM (:issue:`4467`, :issue:`4075`)
- **Audio** - Added the Global Audio API, to cut down on Youtube 429 errors and allow Spotify playback past user's quota. (:issue:`4446`)
- **Audio** - Added persistent queues, allowing for queues to be restored on a bot restart or cog reload (:issue:`4446`)
- **Audio** - Added ``[p]audioset restart``, allowing for Lavalink connection to be restarted (:issue:`4446`)
- **Audio** - Added ``[p]audioset autodeafen``, allowing for bot to auto-deafen itself when entering voice channel (:issue:`4446`)
- **Audio** - Added ``[p]audioset mycountrycode``, allowing Spotify search locale per user (:issue:`4446`)
- **Audio** - Added ``[p]llsetup java``, allowing for a custom Java executable path (:issue:`4446`)
- **Audio** - Added ``[p]llset info`` to show Lavalink settings (:issue:`4527`)
- **Audio** - Added ``[p]audioset logs`` to download Lavalink logs if the Lavalink server is set to internal (:issue:`4527`)
- **Dev** - Added ``[p]repl pause`` to pause/resume the REPL session in the current channel (:issue:`4366`)
- **Mod** - Added ``[p]modset mentionspam strict`` allowing for duplicated mentions to count towards the mention spam cap (:issue:`4359`)
- **Mod** - Added a default tempban duration for ``[p]tempban`` (:issue:`4473`, :issue:`3992`)
- **Mutes** - Added ``[p]muteset forcerole`` to make mutes role based, instead of permission based (:issue:`3634`)
- **Mutes** - Added an optional time argument to all mutes, to specify when the user should be unmuted (:issue:`3634`)
- **Trivia Lists** - Added new MLB trivia list (:issue:`4455`)
- **Trivia Lists** - Added new Who's That Pokémon - Gen. IV trivia list (:issue:`4434`)
- **Trivia Lists** - Added new Hockey trivia list (:issue:`4384`)

Enhancements
************

- Replaced a few instances of Red with the bot name in command docstrings (:issue:`4470`)
- **Core Bot** - Added a default color field to ``[p]set showsettings`` (:issue:`4498`, :issue:`4497`)
- **Core Bot** - Added the datapath and metadata file to ``[p]debuginfo`` (:issue:`4524`)
- **Core Bot** - Added a list of disabled intents to ``[p]debuginfo`` (:issue:`4423`)
- **Core Bot** - Bumped discord.py dependency to version 1.5.1 (:issue:`4423`)
- **Audio** - Removed lavalink logs from being added to backup (:issue:`4453`, :issue:`4452`)
- **Audio** - Removed stream durations from being in queue duration (:issue:`4513`)
- **Cleanup** - Allowed ``[p]cleanup self`` to work in DMs for all users (:issue:`4481`)
- **Economy** - Added an embed option for ``[p]leaderboard`` (:issue:`4184`, :issue:`4104`)
- **Mod** - Added an option to ban users not in the guild to ``[p]ban`` (:issue:`4422`, :issue:`4419`)
- **Mod** - Renamed ``[p]hackban`` to ``[p]massban``, keeping ``[p]hackban`` as an alias, allowing for multiple users to be banned at once (:issue:`4422`, :issue:`4419`)
- **Mutes** - Changed ``[p]mute`` to only handle serverwide muting, ``[p]mute voice`` and ``[p]mute channel`` have been moved to separate commands called ``[p]mutechannel`` and ``[p]mutevoice`` (:issue:`3634`)
- **Mutes** - Mute commands can now take multiple user arguments, to mute multiple users at a time (:issue:`3634`)
- **Warnings** - Added bool arguments to toggle commands to improve consistency (:issue:`4409`)

.. _important-341-1:

Removals
********

- **Mod** - Moved mutes to a separate, individual cog (:issue:`3634`)

Fixes
*****

- Fixed grammar in places scattered throughout bot (:issue:`4500`)
- Properly define supported Python versions to be lower than 3.9 (:issue:`4538`)
- **Core Bot** - Fixed an incorrect error being reported on ``[p]set name`` when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- **Core Bot** - Fixed ``[p]set nickname`` erroring when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- **Core Bot** - Fixed an ungraceful error being raised when running ``[p]traceback`` with closed DMs (:issue:`4329`)
- **Core Bot** - Fixed errors that could arise from invalid URLs in ``[p]set avatar`` (:issue:`4437`)
- **Core Bot** - Fixed an error being raised with ``[p]set nickname`` when no nickname was provided (:issue:`4451`)
- **Core Bot** - Fixed and clarified errors being raised with ``[p]set username`` (:issue:`4463`)
- **Core Bot** - Fixed an ungraceful error being raised when the output of ``[p]unload`` is larger than 2k characters (:issue:`4469`)
- **Core Bot** - Fixed an ungraceful error being raised when running ``[p]choose`` with empty options (:issue:`4499`)
- **Core Bot** - Fixed an ungraceful error being raised when a bot left a guild while a menu was open (:issue:`3902`)
- **Core Bot** - Fixed info missing on the non-embed version of ``[p]debuginfo`` (:issue:`4524`)
- **Audio** - Scattered grammar and typo fixes (:issue:`4446`)
- **Audio** - Fixed Bandcamp playback (:issue:`4504`)
- **Audio** - Fixed YouTube playlist playback (:issue:`4504`)
- **Audio** - Fixed YouTube searching issues (:issue:`4504`)
- **Audio** - Fixed YouTube age restricted track playback (:issue:`4504`)
- **Audio** - Fixed the Audio cog not being translated when setting locale (:issue:`4492`, :issue:`4495`)
- **Audio** - Fixed tracks getting stuck at 0:00 after long player sessions (:issue:`4529`)
- **CustomCommands** - Fixed an ungraceful error being thrown on ``[p]cc edit`` (:issue:`4325`)
- **General** - Fixed issues with text not being properly URL encoded (:issue:`4024`)
- **General** - Fixed an ungraceful error occurring when a title is longer than 256 characters in ``[p]urban`` (:issue:`4474`)
- **General** - Changed "boosters" to "boosts" in ``[p]serverinfo`` to clarify what the number represents (:issue:`4507`)
- **Mod** - Fixed nicknames not being properly stored and logged (:issue:`4131`)
- **Mod** - Fixed plural typos in ``[p]userinfo`` (:issue:`4397`, :issue:`4379`)
- **Modlog** - Fixed an error being raised when running ``[p]casesfor`` and ``[p]case`` (:issue:`4415`)
- **Modlog** - Long reasons in Modlog are now properly shortened in message content (:issue:`4541`)
- **Trivia Lists** - Fixed incorrect order of Machamp and Machoke questions (:issue:`4424`)
- **Warnings** - Fixed users being able to warn users above them in hierarchy (:issue:`4100`)


Developer changelog
-------------------

| **Important:**
| #. Red now allows users to set locale per guild, which requires 3rd-party cogs to set contextual locale manually in code ran outside of command's context. See the `New Functionality changelog below <important-dev-341-1>` for more information.

.. _important-dev-341-1:

New Functionality
*****************

- Added API for setting contextual locales (:issue:`3896`, :issue:`1970`)

    - New function added: `redbot.core.i18n.set_contextual_locales_from_guild()`
    - Contextual locale is automatically set for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information

- Added `bot.remove_shared_api_services() <Red.remove_shared_api_services()>` to remove all keys and tokens associated with an API service (:issue:`4370`)
- Added an option to return all tokens for an API service if ``service_name`` is not specified in `bot.get_shared_api_tokens() <Red.get_shared_api_tokens()>` (:issue:`4370`)
- Added `bot.get_or_fetch_user() <Red.get_or_fetch_user()>` and `bot.get_or_fetch_member() <Red.get_or_fetch_member()>` methods (:issue:`4403`, :issue:`4402`)
- Added ``[all]`` and ``[dev]`` extras to the ``Red-DiscordBot`` package (:issue:`4443`)
- **Downloader** - Added JSON schema files for ``info.json`` files (:issue:`4375`)
- **Modlog** - Added ``last_known_username`` parameter to `modlog.create_case()` function (:issue:`4326`)
- **Utility Functions** - Added `redbot.core.utils.get_end_user_data_statement()` and `redbot.core.utils.get_end_user_data_statement_or_raise()` to attempt to fetch a cog's End User Data Statement (:issue:`4404`)
- **Utility Functions** - Added `redbot.core.utils.chat_formatting.quote()` to quote text in a message (:issue:`4425`)

Enhancements
************

- Moved ``redbot.core.checks.bot_in_a_guild()`` to `redbot.core.commands.bot_in_a_guild()` (old name has been left as an alias) (:issue:`4515`, :issue:`4510`)
- **Bank** - Bank API methods now consistently throw TypeError if a non-integer amount is supplied (:issue:`4376`)
- **Modlog** - Added an option to accept a ``discord.Object`` in `modlog.create_case()` (:issue:`4326`)

Deprecations
************

- **Utility Functions** - Deprecated ``redbot.core.utils.mod.is_allowed_by_hierarchy`` (:issue:`4435`)

Fixes
*****

- **Modlog** - Fixed an error being raised with a deleted channel in `Case.message_content()` (:issue:`4415`)


Documentation changes
---------------------

New Documentation
*****************

- Added custom group documentation and tutorial (:issue:`4416`, :issue:`2896`)
- Added guide to creating a Bot Application in Discord Developer Portal, with enabling intents (:issue:`4502`)

Enhancements
************

- Clarified that naive ``datetime`` objects will be treated as local times for parameters ``created_at`` and ``until`` in `modlog.create_case()` (:issue:`4389`)
- Replaced the link to the approved repository list on CogBoard and references to ``cogs.red`` with a link to new Red Index (:issue:`4439`)
- Improved documentation about arguments in command syntax (:issue:`4058`)


Redbot 3.4.0 (2020-08-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`DevilXD`, :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kablekompany`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`SharkyTheKing`, :ghuser:`thisisjvgrace`, :ghuser:`Tinonb`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. Red 3.4 comes with support for data deletion requests. Bot owners should read `red_core_data_statement` to ensure they know what information about their users is stored by the bot.
#. Debian Stretch, Fedora 30 and lower, and OpenSUSE Leap 15.0 and lower are no longer supported as they have already reached end of life.
#. There's been a change in behavior of ``[p]tempban``. Look at `Enhancements changelog for Mod cog <important-340-1>` for full details.
#. There's been a change in behavior of announcements in Admin cog. Look at `Enhancements changelog for Admin cog <important-340-1>` for full details.
#. Red 3.4 comes with breaking changes for cog developers. Look at `Developer changelog <important-340-3>` for full details.

End-user changelog
------------------

Security
********

- **Streams** - Fixed critical vulnerability that could allow remote code execution (CVE-2020-15147), see `security advisory GHSA-7257-96vg-qf6x <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-7257-96vg-qf6x>`__ for more information (:issue:`4183`)

New Functionality
*****************

- **Core Bot** - Added per-guild cog disabling (:issue:`4043`, :issue:`3945`)

    - Bot owners can set the default state for a cog using ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands
    - Guild owners can enable/disable cogs for their guild using ``[p]command disablecog`` and ``[p]command enablecog`` commands
    - Cogs disabled in the guild can be listed with ``[p]command listdisabledcogs``

- **Core Bot** - Added support for data deletion requests; see `red_core_data_statement` for more information (:issue:`4045`)
- **Core Bot** - Added ``[p]helpset showsettings`` command (:issue:`4013`, :issue:`4022`)
- **Mod** - Users can now set mention spam triggers which will warn or kick the user. See ``[p]modset mentionspam`` for more information (:issue:`3786`, :issue:`4038`)
- **Trivia Lists** - Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- **Trivia Lists** - Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)

.. _important-340-1:

Enhancements
************

- ``[p]set nickname``, ``[p]set serverprefix``, ``[p]streamalert``, and ``[p]streamset`` commands now can be run by users with permissions related to the actions they're making (:issue:`4109`)
- **Core Bot** - Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)
- **Core Bot** - ``[p]licenseinfo`` now has a 3 minute cooldown to prevent a single user from spamming channel by using it (:issue:`4110`)
- **Core Bot** - Updated Red's emoji usage to ensure consistent rendering accross different devices (:issue:`4106`, :issue:`4105`, :issue:`4127`)
- **Core Bot** - Whitelist and blacklist are now called allowlist and blocklist. Old names have been left as aliases (:issue:`4138`)
- **Admin** - ``[p]announce`` will now only send announcements to guilds that have explicitly configured text channel to send announcements to using ``[p]announceset channel`` command (:issue:`4088`, :issue:`4089`)
- **Downloader** - ``[p]cog info`` command now shows end user data statement made by the cog creator (:issue:`4169`)
- **Downloader** - ``[p]cog update`` command will now notify the user if cog's end user data statement has changed since last update (:issue:`4169`)
- **General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- **General** - Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)
- **Mod** - ``[p]tempban`` now respects default days setting (``[p]modset defaultdays``) (:issue:`3993`)
- **Mod** - ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- **Mod** - Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)
- **Modlog** - Added timestamp to text version of ``[p]casesfor`` and ``[p]case`` commands (:issue:`4118`, :issue:`4137`)
- **Streams** - Stream alerts will no longer make roles temporarily mentionable if bot has "Mention @everyone, @here, and All Roles" permission in the channel (:issue:`4182`)
- **Streams** - Hitbox commands have been renamed to smashcast (:issue:`4161`)
- **Streams** - Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

Removals
********

- **Streams** - Mixer service has been closed and for that reason we've removed support for it from the cog (:issue:`4072`)

Fixes
*****

- Fixed timestamp storage in few places in Red (:issue:`4017`)


.. _important-340-3:

Developer changelog
-------------------

| **Important:**
| #. Red now offers cog disabling API, which should be respected by 3rd-party cogs in guild-related actions happening outside of command's context. See the `Core Bot changelog below <important-dev-340-1>` for more information.
| #. Red now provides data request API, which should be supported by all 3rd-party cogs. See the changelog entries in the `Core Bot changelog below <important-dev-340-1>` for more information.

Breaking Changes
****************

- By default, none of the ``.send()`` methods mention roles or ``@everyone/@here`` (:issue:`3845`)

    - see `discord.AllowedMentions` and ``allowed_mentions`` kwarg of ``.send()`` methods, if your cog requires to mention roles or ``@everyone/@here``

- `Context.maybe_send_embed()` now supresses all mentions, including user mentions (:issue:`4192`)
- The default value of the ``filter`` keyword argument has been changed to ``None`` (:issue:`3845`)
- Cog package names (i.e. name of the folder the cog is in and the name used when loading the cog) now have to be `valid Python identifiers <https://docs.python.org/3/reference/lexical_analysis.html#identifiers>`__ (:issue:`3605`, :issue:`3679`)
- Method/attribute names starting with ``red_`` or being in the form of ``__red_*__`` are now reserved. See `version_guarantees` for more information (:issue:`4085`)
- `humanize_list()` no longer raises `IndexError` for empty sequences (:issue:`2982`)
- Removed things past deprecation time: (:issue:`4163`)

    - ``redbot.core.commands.APIToken``
    - ``loop`` kwarg from `bounded_gather_iter()`, `bounded_gather()`, and `start_adding_reactions()`

.. _important-dev-340-1:

New Functionality
*****************

- Added cog disabling API (:issue:`4043`, :issue:`3945`)

    - New methods added: `bot.cog_disabled_in_guild() <Red.cog_disabled_in_guild()>`, `bot.cog_disabled_in_guild_raw() <Red.cog_disabled_in_guild_raw()>`
    - Cog disabling is automatically applied for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information

- Added data request API (:issue:`4045`,  :issue:`4169`)

    - New special methods added to `redbot.core.commands.Cog`: `red_get_data_for_user()` (documented provisionally), `red_delete_data_for_user()`
    - New special module level variable added: ``__red_end_user_data_statement__``
    - These methods and variables should be added by all cogs according to their documentation; see `recommendations-for-cog-creators` for more information
    - New ``info.json`` key added: ``end_user_data_statement``; see `Info.json format documentation <info-json-format>` for more information

- Added `bot.message_eligible_as_command() <Red.message_eligible_as_command()>` utility method which can be used to determine if a message may be responded to as a command (:issue:`4077`)
- Added a provisional API for replacing the help formatter. See `documentation <framework-commands-help>` for more details (:issue:`4011`)
- `commands.NoParseOptional <NoParseOptional>` is no longer provisional and is now fully supported part of API (:issue:`4142`)

Enhancements
************

- `bot.ignored_channel_or_guild() <Red.ignored_channel_or_guild()>` now accepts `discord.Message` objects (:issue:`4077`)
- Autohelp in group commands is now sent *after* invoking the group, which allows before invoke hooks to prevent autohelp from getting triggered (:issue:`4129`)
- **Utility Functions** - `humanize_list()` now accepts ``locale`` and ``style`` keyword arguments. See its documentation for more information (:issue:`2982`)
- **Utility Functions** - `humanize_list()` is now properly localized (:issue:`2906`, :issue:`2982`)
- **Utility Functions** - `humanize_list()` now accepts empty sequences (:issue:`2982`)
- **Utility Functions** - `bordered()` now uses ``+`` for corners if keyword argument ``ascii_border`` is set to `True` (:issue:`4097`)
- **Vendored packages** - Updated ``discord.ext.menus`` vendor (:issue:`4167`)

Fixes
*****

- RPC functionality no longer makes Red hang for a minute on shutdown (:issue:`4134`, :issue:`4143`)
- Red no longer fails to run subcommands of a command group allowed or denied by permission hook (:issue:`3956`)


Documentation changes
---------------------

New Documentation
*****************

- Added admin user guide (:issue:`3081`)
- Added alias user guide (:issue:`3084`)
- Added bank user guide (:issue:`4149`)

Removals
********

- Removed install instructions for Debian Stretch (:issue:`4099`)


Redbot 3.3.12 (2020-08-18)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`douglas-cpp`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MeatyChunks`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

End-user changelog
------------------

Security
********

- **Streams** - Fixed critical vulnerability that could allow remote code execution (CVE-2020-15147), see `security advisory GHSA-7257-96vg-qf6x <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-7257-96vg-qf6x>`__ for more information (:issue:`4183`)

New Functionality
*****************

- **Trivia Lists** - Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- **Trivia Lists** - Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)

Enhancements
************

- **Core Bot** - Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)
- **General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- **General** - Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)
- **Mod** - ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- **Mod** - Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)
- **Streams** - Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)


Redbot 3.3.11 (2020-08-10)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`Flame`, :ghuser:`jack1142`, :ghuser:`MeatyChunks`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

End-user changelog
------------------

Security
********

- **Trivia** - Fixed critical vulnerability that could allow remote code execution (CVE-2020-15140), see `security advisory GHSA-7257-96vg-qf6x <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-55j9-849x-26h4>`__ for more information (:issue:`4175`)

Fixes
*****

- **Audio** - Audio should now work again on all voice regions (:issue:`4162`, :issue:`4168`)
- **Audio** - Removed an edge case where an unfriendly error message was sent in Audio cog (:issue:`3879`)
- **Cleanup** - Fixed a bug causing ``[p]cleanup`` commands to clear all messages within last 2 weeks when ``0`` is passed as the amount of messages to delete (:issue:`4114`, :issue:`4115`)
- **CustomCommands** - ``[p]cc show`` now sends an error message when command with the provided name couldn't be found (:issue:`4108`)
- **Downloader** - ``[p]findcog`` no longer fails for 3rd-party cogs without any author (:issue:`4032`, :issue:`4042`)
- **Downloader** - Update commands no longer crash when a different repo is added under a repo name that was once used (:issue:`4086`)
- **Permissions** - ``[p]permissions removeserverrule`` and ``[p]permissions removeglobalrule`` no longer error when trying to remove a rule that doesn't exist (:issue:`4028`, :issue:`4036`)
- **Warnings** - ``[p]warn`` now sends an error message (instead of no feedback) when an unregistered reason is used by someone who doesn't have Administrator permission (:issue:`3839`, :issue:`3840`)


Redbot 3.3.10 (2020-07-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`

End-user changelog
------------------

New Functionality
*****************

- **Downloader** - Added ``[p]cog listpinned`` subcommand to see currently pinned cogs (:issue:`3974`)
- **Filter** - Added ``[p]filter list`` to show filtered words, and removed DMs when no subcommand was passed (:issue:`3973`)
- **Trivia Lists** - Added new ``lotr`` trivia list (:issue:`3980`)
- **Trivia Lists** - Added new ``r6seige`` trivia list (:issue:`4026`)

Enhancements
************

- **Core Bot** - Bumped the Discord.py requirement from 1.3.3 to 1.3.4 (:issue:`4053`)
- **Core Bot** - Added settings view commands for nearly all cogs. (:issue:`4041`)
- **Core Bot** - Added more strings to be fully translatable by i18n. (:issue:`4044`)
- **Core Bot** - Red now prints a link to Getting Started guide if the bot isn't in any server (:issue:`3906`)
- **Core Bot** - Added the option of using dots in the instance name when creating your instances (:issue:`3920`)
- **Core Bot** - Added a confirmation when using hyphens in instance names to discourage the use of them (:issue:`3920`)
- **Core Bot** - Clarified that ``[p]embedset user`` only affects commands executed in DMs (:issue:`3972`, :issue:`3953`)
- **Audio** - Added information about internally managed jar to ``[p]audioset info`` (:issue:`3915`)
- **Downloader** - Added embed version of ``[p]findcog`` (:issue:`3965`, :issue:`3944`)
- **Mod** - Added option to delete messages within the passed amount of days with ``[p]tempban`` (:issue:`3958`)
- **Mod** - Reduced the number of API calls made to the storage APIs (:issue:`3910`)
- **Mod** - Prevented an issue whereby the author may lock him self out of using the bot via whitelists (:issue:`3903`)
- **Mod** - Improved error response in ``[p]modset banmentionspam`` (:issue:`3951`, :issue:`3949`)
- **Modlog** - Improved error response in ``[p]modlogset modlog`` (:issue:`3951`, :issue:`3949`)
- **Permissions** - Uploaded YAML files now accept integer commands without quotes (:issue:`3987`, :issue:`3185`)
- **Permissions** - Uploaded YAML files now accept command rules with empty dictionaries (:issue:`3987`, :issue:`3961`)
- **Trivia Lists** - Updated ``greekmyth`` to include more answer variations (:issue:`3970`)

Fixes
*****

- **Core Bot** - Fixed delayed help when ``[p]set deletedelay`` is enabled (:issue:`3884`, :issue:`3883`)
- **Core Bot** - Fixed grammar errors and added full stops in various core commands (:issue:`4023`)
- **Audio** - Twitch playback and YouTube searching should be functioning again. (:issue:`4055`)
- **Downloader** - Fixed unnecessary typing when running downloader commands (:issue:`3964`, :issue:`3948`)
- **Downloader** - Fixed ``[p]findcog`` not differentiating between core cogs and local cogs(:issue:`3969`, :issue:`3966`)
- **Image** - Updated instructions for obtaining and setting the GIPHY API key (:issue:`3994`)
- **Mod** - Added the ability to permanently ban a temporarily banned user with ``[p]hackban`` (:issue:`4025`)
- **Mod** - Fixed the passed reason not being used when using ``[p]tempban`` (:issue:`3958`)
- **Mod** - Fixed invite being sent with ``[p]tempban`` even when no invite was set (:issue:`3991`)
- **Mod** - Fixed exceptions being ignored or not sent to log files in special cases (:issue:`3895`)
- **Mod** - Fixed migration owner notifications being sent even when migration was not necessary (:issue:`3911`. :issue:`3909`)
- **Streams** - Fixed Streams cog sending multiple owner notifications about twitch secret not set (:issue:`3901`, :issue:`3587`)
- **Streams** - Fixed old bearer tokens not being invalidated when the API key is updated (:issue:`3990`, :issue:`3917`)
- **Streams** - Fixed commands being translated where they should not be (:issue:`3938`, :issue:`3919`)
- **Trivia Lists** - Fixed URLs in ``whosthatpokemon`` (:issue:`3975`, :issue:`3023`)
- **Trivia Lists** - Fixed trivia files ``leagueults`` and ``sports`` (:issue:`4026`)


Developer changelog
-------------------

New Functionality
*****************

- **Utliity Functions** - Added the utility functions ``map``, ``find``, and ``next`` to `AsyncIter` (:issue:`3921`, :issue:`3887`)
- **Vendored Packages** - Vendor the ``discord.ext.menus`` module (:issue:`4039`)

Enhancements
************

- **Utliity Functions** - Added new ``discord.com`` domain to ``INVITE_URL_RE`` common filter (:issue:`4012`)

Deprecations
************

- Updated deprecation times for ``APIToken``, and loops being passed to various functions to the first minor release (represented by ``X`` in ``3.X.0``) after 2020-08-05 (:issue:`3608`)
- **Downloader** - Updated deprecation warnings for shared libs to reflect that they have been moved for an undefined time (:issue:`3608`)

Fixes
*****

- **Utliity Functions** - Fixed incorrect role mention regex in `MessagePredicate` (:issue:`4030`)


Redbot 3.3.9 (2020-06-12)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`Predeactor`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Bot owners can no longer restrict access to some commands in Permissions cog using global permissions rules. Look at `Security changelog <important-339-2>` for full details.
#. There's been a change in behavior of warning messages. Look at `New Functionality changelog <important-339-1>` for full details.

End-user changelog
------------------

.. _important-339-2:

Security
********

- **Mod** - ``[p]tempban`` now properly respects Discord's hierarchy rules (:issue:`3957`)

    **NOTE**: If you can't update immediately, we recommend disabling the affected command until you can.

- **Permissions** - **Both global and server rules** can no longer prevent guild owners from accessing commands for changing server rules. Bot owners can still use ``[p]command disable`` if they wish to completely disable any command in Permissions cog (:issue:`3955`, :issue:`3107`)

  Full list of affected commands:

  - ``[p]permissions acl getserver``
  - ``[p]permissions acl setserver``
  - ``[p]permissions acl updateserver``
  - ``[p]permissions addserverrule``
  - ``[p]permissions removeserverrule``
  - ``[p]permissions setdefaultserverrule``
  - ``[p]permissions clearserverrules``
  - ``[p]permissions canrun``
  - ``[p]permissions explain``

.. _important-339-1:

New Functionality
*****************

- **Warnings** - Warnings sent to users don't show the moderator who warned the user by default now. Newly added ``[p]warningset showmoderators`` command can be used to switch this behaviour (:issue:`3781`)

Enhancements
************

- **Core Bot** - ``[p]info`` command can now be used when bot doesn't have Embed Links permission (:issue:`3907`, :issue:`3102`)
- **Core Bot** - Red's start up message now shows storage type (:issue:`3935`)
- **Core Bot** - Improved instructions on obtaining user ID in help of ``[p]dm`` command (:issue:`3946`)
- **Alias** - ``[p]alias global`` group, ``[p]alias help``, and ``[p]alias show`` commands can now be used in DMs (:issue:`3941`, :issue:`3940`)
- **Bank** - ``[p]bankset`` now displays bank's scope (:issue:`3954`)

Fixes
*****

- Added missing help message for Downloader, Reports and Streams cogs (:issue:`3892`)
- **Core Bot** - Fixed ungraceful error that happened in ``[p]set custominfo`` when provided text was too long (:issue:`3923`)
- **Core Bot** - Cooldown in ``[p]contact`` no longer applies when it's used without any arguments (:issue:`3942`)
- **Audio** - Audio now properly ignores streams when max length is enabled (:issue:`3878`, :issue:`3877`)
- **Audio** - Commands that should work in DMs no longer error (:issue:`3880`)
- **Audio** - Fixed ``[p]audioset autoplay`` being available in DMs (:issue:`3899`)
- **Audio** - Typo fix (:issue:`3889`, :issue:`3900`)
- **Filter** - Fixed behavior of detecting quotes in commands for adding/removing filtered words (:issue:`3925`)
- **Mod** - Preemptive fix for d.py 1.4 (:issue:`3891`)
- **Warnings** - Warn channel functionality has been fixed (:issue:`3781`)

Developer changelog
-------------------

New Functionality
*****************

- Added `bot.set_prefixes() <Red.set_prefixes()>` method that allows developers to set global/server prefixes (:issue:`3890`)


Documentation changes
---------------------

Enhancements
************

- Added Oracle Cloud to free hosting section in :ref:`host-list` (:issue:`3916`)


Redbot 3.3.8 (2020-05-29)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Bakersbakebread`, :ghuser:`DariusStClair`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`qaisjp`, :ghuser:`Tobotimus`

End-user changelog
------------------

New Functionality
*****************

- **Audio** - Added new option (settable with ``[p]audioset lyrics``) that makes Audio cog prefer (prioritize) tracks with lyrics (:issue:`3519`)
- **Audio** - Added global daily (historical) queues (:issue:`3518`)
- **Audio** - Added ``[p]audioset countrycode`` that allows to set the country code for spotify searches (:issue:`3528`)

Enhancements
************

- Few clarifications and typo fixes in few command help docstrings (:issue:`3817`, :issue:`3823`, :issue:`3837`, :issue:`3851`, :issue:`3861`)
- **Core Bot** - Red now includes information on how to update when sending information about being out of date (:issue:`3744`)
- **Alias** - ``[p]alias help`` should now work more reliably (:issue:`3864`)
- **Audio** - ``[p]local play`` no longer enqueues tracks from nested folders (:issue:`3528`)
- **Audio** - ``[p]disconnect`` now allows to disconnect if both DJ mode and voteskip aren't enabled (:issue:`3502`, :issue:`3485`)
- **Audio** - Many UX improvements and fixes, including, among other things:

  - Creating playlists without explicitly passing ``-scope`` no longer causes errors (:issue:`3500`)
  - ``[p]playlist list`` now shows all accessible playlists if ``--scope`` flag isn't used (:issue:`3518`)
  - ``[p]remove`` now also accepts a track URL in addition to queue index (:issue:`3201`)
  - ``[p]playlist upload`` now accepts a playlist file uploaded in the message with a command (:issue:`3251`)
  - Commands now send friendly error messages for common errors like lost Lavalink connection or bot not connected to voice channel (:issue:`3503`, :issue:`3528`, :issue:`3353`, :issue:`3712`)
- **Mod** - ``[p]userinfo`` now shows default avatar when no avatar is set (:issue:`3819`)

Fixes
*****

- **Core Bot** - Made important fixes to how PostgreSQL data backend saves data in bulks (:issue:`3829`)
- **Core Bot** - Fixed ``[p]localwhitelist`` and ``[p]localblacklist`` commands (:issue:`3857`)
- **Core Bot** - Using backslashes in bot's username/nickname no longer causes issues (:issue:`3826`, :issue:`3825`)
- **Admin** - Fixed server lock (:issue:`3815`, :issue:`3814`)
- **Alias** - Added pagination to ``[p]alias list`` and ``[p]alias global list`` to avoid errors for users with a lot of aliases (:issue:`3844`, :issue:`3834`)
- **Audio** - Twitch playback is functional once again (:issue:`3873`)
- **Audio** - Recent errors with YouTube playback should be resolved (:issue:`3873`)
- **Audio** - Fixed ``[p]local search`` (:issue:`3528`, :issue:`3501`)
- **Audio** - Local folders with special characters should work properly now (:issue:`3528`, :issue:`3467`)
- **Audio** - Audio no longer fails to take the last spot in the voice channel with user limit (:issue:`3528`)
- **Audio** - Fixed ``[p]playlist dedupe`` not removing tracks (:issue:`3518`)
- **CustomCommands** - ``[p]customcom create`` no longer allows spaces in custom command names (:issue:`3816`)
- **Modlog** - Fixed (again) ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3805`, :issue:`3784`, :issue:`3778`)
- **Permissions** - Commands for settings ACL using yaml files now properly works on PostgreSQL data backend (:issue:`3829`, :issue:`3796`)
- **Warnings** - Warnings cog no longer allows to warn bot users (:issue:`3855`, :issue:`3854`)


Developer changelog
-------------------

| **Important:**
| If you're using RPC, please see the full annoucement about current state of RPC in main Red server
  `by clicking here <https://discord.com/channels/133049272517001216/411381123101491200/714560168465137694>`__.

Enhancements
************

- Red now inherits from `discord.ext.commands.AutoShardedBot` for better compatibility with code expecting d.py bot (:issue:`3822`)
- All bot owner IDs can now be found under ``bot.owner_ids`` attribute (:issue:`3793`)

  -  Note: If you want to use this on bot startup (e.g. in cog's initialisation), you need to await ``bot.wait_until_red_ready()`` first

Fixes
*****

- Libraries using ``pkg_resources`` (like ``humanize`` or ``google-api-python-client``) that were installed through Downloader should now work properly (:issue:`3843`)
- **Downloader** - Downloader no longer removes the repo when it fails to load it (:issue:`3867`)


Documentation changes
---------------------

Enhancements
************

- Added information about provisional status of RPC (:issue:`3862`)
- Revised install instructions (:issue:`3847`)
- Improved navigation in `document about updating Red <update_red>` (:issue:`3856`, :issue:`3849`)


Redbot 3.3.7 (2020-04-28)
=========================

This is a hotfix release fixing issue with generating messages for new cases in Modlog.


Redbot 3.3.6 (2020-04-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`yamikaitou`

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added ``[p]set avatar remove`` subcommand for removing bot's avatar (:issue:`3757`)
- **CustomCommands** - Added ``[p]cc raw`` command that gives you the raw response of a custom command for ease of copy pasting (:issue:`3795`)

Enhancements
************

- **Core Bot** - Various optimizations

  - Reduced calls to data backend when loading bot's commands (:issue:`3764`)
  - Reduced calls to data backend when showing help for cogs/commands (:issue:`3766`)
  - Improved performance for bots with big amount of guilds (:issue:`3767`)
  - Mod cog no longer fetches guild's bans every 60 seconds when handling unbanning for tempbans (:issue:`3783`)
  - Reduced the bot load for messages starting with a prefix when fuzzy search is disabled (:issue:`3718`)
  - Aliases in Alias cog are now cached for better performance (:issue:`3788`)
- **Core Bot** - ``[p]set avatar`` now supports setting avatar using attachment (:issue:`3747`)
- **Core Bot** - ``[p]debuginfo`` now shows used storage type (:issue:`3794`)
- **Trivia Lists** - Updated ``leagueoflegends`` list with new changes to League of Legends (`b8ac70e <https://github.com/Cog-Creators/Red-DiscordBot/commit/b8ac70e59aa1328f246784f14f992d6ffe00d778>`__)

Fixes
*****

- **Core Bot** - Converting from and to Postgres driver with ``redbot-setup convert`` have been fixed (:issue:`3714`, :issue:`3115`)
- **Core Bot** - Fixed big delays in commands that happened when the bot was owner-less (or if it only used co-owners feature) and command caller wasn't the owner (:issue:`3782`)
- **Core Bot** - Fixed list of ignored channels that is shown in ``[p]ignore``/``[p]unignore`` (:issue:`3746`)
- **Audio** - Age-restricted tracks, live streams, and mix playlists from YouTube should work in Audio again (:issue:`3791`)
- **Audio** - Soundcloud's sets and playlists with more than 50 tracks should work in Audio again (:issue:`3791`)
- **Modlog** - Fixed ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3784`, :issue:`3778`)
- **Streams** - Fixed incorrect stream URLs for Twitch channels that have localised display name (:issue:`3773`, :issue:`3772`)
- **Trivia** - Fixed the error in ``[p]trivia stop`` that happened when there was no ongoing trivia session in the channel (:issue:`3774`)
- **Trivia Lists** - Corrected spelling of Compact Disc in ``games`` list (:issue:`3759`, :issue:`3758`)


Developer changelog
-------------------

New Functionality
*****************

- **Utility Functions** - Added `redbot.core.utils.AsyncIter` utility class which allows you to wrap regular iterable into async iterator yielding items and sleeping for ``delay`` seconds every ``steps`` items (:issue:`3767`, :issue:`3776`)

Enhancements
************

- **Utility Functions** - `bold()`, `italics()`, `strikethrough()`, and `underline()` now accept ``escape_formatting`` argument that can be used to disable escaping of markdown formatting in passed text (:issue:`3742`)

Fixes
*****

- **Config** - JSON driver will now properly have only one lock per cog name (:issue:`3780`)


Documentation changes
---------------------

New Documentation
*****************

- Added `document about updating Red <update_red>` (:issue:`3790`)
- Updated install docs to include Ubuntu 20.04 (:issue:`3792`)

Enhancements
************

- ``pyenv`` instructions will now update ``pyenv`` if it's already installed (:issue:`3740`)
- Updated Python version in ``pyenv`` instructions (:issue:`3740`)


Redbot 3.3.5 (2020-04-09)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`

End-user changelog
------------------

Enhancements
************

- **Core Bot** - "Outdated" field no longer shows in ``[p]info`` when Red is up-to-date (:issue:`3730`)

Fixes
*****

- **Alias** - Fixed regression in ``[p]alias add`` that caused it to reject commands containing arguments (:issue:`3734`)


Redbot 3.3.4 (2020-04-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`kennnyshiwa`

End-user changelog
------------------

Enhancements
************

- **Alias** - ``[p]alias add`` now sends an error when command user tries to alias doesn't exist (:issue:`3710`, :issue:`3545`)

Fixes
*****

- **Core Bot** - Fixed checks related to bank's global state that were used in commands in Bank, Economy and Trivia cogs (:issue:`3707`)

Developer changelog
-------------------

Enhancements
************

- Bump dependencies, including update to discord.py 1.3.3 (:issue:`3723`)
- **Utility Functions** - `redbot.core.utils.common_filters.filter_invites` now filters ``discord.io/discord.li`` invites links (:issue:`3717`)

Fixes
*****

- **Utility Functions** - Fixed false-positives in `redbot.core.utils.common_filters.filter_invites` (:issue:`3717`)

Documentation changes
---------------------

Enhancements
************

- Versions of pre-requirements are now included in Windows install guide (:issue:`3708`)


Redbot 3.3.3 (2020-03-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`AnonGuy`, :ghuser:`Dav-Git`, :ghuser:`FancyJesse`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Security
********

- **Cleanup** - Removed regex support in ``[p]cleanup self`` (:issue:`3704`)

New Functionality
*****************

- **Core Bot** - Added ``[p]set regionalformat`` command that allows users to set regional formatting that is different from bot's locale (:issue:`3677`, :issue:`3588`)
- **Cleanup** - Added ``[p]cleanup spam`` command that deletes duplicate messages from the last X messages and keeps only one copy (:issue:`3688`)
- **CustomCommands** - Added ``[p]cc search`` command that allows users to search through created custom commands (:issue:`2573`)
- **Trivia** - Added ``[p]triviaset custom upload/delete/list`` commands for managing custom trivia lists from Discord (:issue:`3420`, :issue:`3307`)
- **Warnings** - Sending warnings to warned user can now be disabled with ``[p]warnset toggledm`` command (:issue:`2929`, :issue:`2800`)
- **Warnings** - Added ``[p]warnset warnchannel`` command that allows to set a channel where warnings should be sent to instead of the channel command was called in (:issue:`2929`, :issue:`2800`)
- **Warnings** - Added ``[p]warnset togglechannel`` command that allows to disable sending warn message in guild channel (:issue:`2929`, :issue:`2800`)

Enhancements
************

- **Core Bot** - Delete delay for command messages has been moved from Mod cog to Core (:issue:`3638`, :issue:`3636`)
- **Core Bot** - ``[p]set locale`` allows any valid locale now, not just locales for which Red has translations (:issue:`3676`, :issue:`3596`)
- **Core Bot** - Permissions for commands in Bank, Economy and Trivia cogs can now be overridden by Permissions cog (:issue:`3672`, :issue:`3233`)
- **Core Bot** - Added ``[p]set playing`` and ``[p]set streaming`` aliases for respectively ``[p]set game`` and ``[p]set stream`` (:issue:`3646`, :issue:`3590`)
- **Core Bot** - Command errors (i.e. command on cooldown, dm-only and guild-only commands, etc) can now be translated (:issue:`3665`, :issue:`2988`)
- **Core Bot** - ``redbot-setup`` now prints link to Getting started guide at the end of the setup (:issue:`3027`)
- **Downloader** - ``[p]cog checkforupdates`` now includes information about cogs that can't be installed due to Red/Python version requirements (:issue:`3678`, :issue:`3448`)
- **Downloader** - Improved error messages for unexpected errors in ``[p]repo add`` (:issue:`3656`)
- **General** - Added more detailed mode to ``[p]serverinfo`` command that can be accessed with ``[p]serverinfo 1`` (:issue:`2382`, :issue:`3659`)
- **Image** - Users can now specify how many images should be returned in ``[p]imgur search`` and ``[p]imgur subreddit`` using ``[count]`` argument (:issue:`3667`, :issue:`3044`)
- **Image** - ``[p]imgur search`` and ``[p]imgur subreddit`` now return one image by default (:issue:`3667`, :issue:`3044`)
- **Mod** - ``[p]userinfo`` now shows user's activities (:issue:`3669`)
- **Mod** - ``[p]userinfo`` now shows status icon near the username (:issue:`3669`)
- **Modlog** - Modlog's cases now keep last known username to prevent losing that information from case's message on edit (:issue:`3674`, :issue:`3443`)
- **Permissions** - Commands for setting default rules now error when user tries to deny access to command designated as being always available (:issue:`3504`, :issue:`3465`)
- **Streams** - Preview picture for YouTube stream alerts is now bigger (:issue:`3689`, :issue:`3685`)
- **Streams** - Failures in Twitch API authentication are now logged (:issue:`3657`)
- **Warnings** - ``[p]warn`` now tells the moderator when bot wasn't able to send the warning to the user (:issue:`3653`, :issue:`3633`)

Fixes
*****

- **Core Bot** - Fixed various bugs with blacklist and whitelist (:issue:`3643`, :issue:`3642`)
- **Core Bot** - Outages of ``pypi.org`` no longer prevent the bot from starting (:issue:`3663`)
- **Core Bot** - Fixed formatting of help strings in fuzzy search results (:issue:`3673`, :issue:`3507`)
- **Core Bot** - Fixed few deprecation warnings related to menus and uvloop (:issue:`3644`, :issue:`3700`)
- **Core Bot** - ``[p]set game`` no longer errors when trying to clear the status (:issue:`3630`, :issue:`3628`)
- **Core Bot** - All owner notifcations in Core now use proper prefixes in messages (:issue:`3632`)
- **Core Bot** - Whitelist and blacklist commands now properly require passing at least one user (or role in case of local whitelist/blacklist) (:issue:`3652`, :issue:`3645`)
- **Downloader** - Fix misleading error appearing when repo name is already taken in ``[p]repo add`` (:issue:`3695`)
- **Downloader** - Prevent encoding errors from crashing ``[p]cog update`` (:issue:`3639`, :issue:`3637`)
- **Mod** - Muting no longer fails if user leaves while applying overwrite (:issue:`3627`)
- **Mod** - Fixed error that happened when Mod cog was loaded for the first time during bot startup (:issue:`3632`, :issue:`3626`)
- **Streams** - Fixed an error that happened when no game was set on Twitch stream (:issue:`3631`)
- **Streams** - YouTube channels with a livestream that doesn't have any current viewer are now properly showing as streaming (:issue:`3690`)
- **Trivia** - Trivia sessions no longer error on payout when winner's balance would exceed max balance (:issue:`3666`, :issue:`3584`)
- **Trivia** - Non-finite numbers can no longer be passed to ``[p]triviaset timelimit``, ``[p]triviaset stopafter`` and ``[p]triviaset payout`` (:issue:`3668`, :issue:`3583`)


Developer changelog
-------------------

Fixes
*****

- Deprecation warnings issued by Red now use correct stack level so that the cog developers can find the cause of them (:issue:`3644`)
- **Dev Cog** - Added ``__name__`` to environment's globals (:issue:`3649`, :issue:`3648`)
- **Utility Functions** - `redbot.core.utils.menus.menu()` now checks permissions *before* trying to clear reactions (:issue:`3589`, :issue:`3145`)


Documentation changes
---------------------

Enhancements
************

- Windows install instructions now use ``choco upgrade`` commands instead of ``choco install`` to ensure up-to-date packages (:issue:`3684`)

Fixes
*****

- Fixed install instructions for Mac (:issue:`3675`, :issue:`3436`)


Redbot 3.3.2 (2020-02-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`chasehult`, :ghuser:`Dav-Git`, :ghuser:`DiscordLiz`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Hedlund01`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`trundler-dev`, :ghuser:`TrustyJAID`, :ghuser:`zephyrkul`

End-user changelog
------------------

New Functionality
*****************

- **Dev Cog** - Allow for top-level `await`, `async for` and `async with` in ``[p]debug`` and ``[p]repl`` commands (:issue:`3508`)
- **Streams** - Added ``[p]streamset timer`` command which can be used to control how often the cog checks for live streams (:issue:`3237`)

Enhancements
************

- **Core Bot** - Ignored guilds/channels and whitelist/blacklist are now cached for performance (:issue:`3472`)
- **Core Bot** - Ignored guilds/channels have been moved from Mod cog to Core (:issue:`3472`)
- **Core Bot** - ``[p]ignore channel`` command can now also ignore channel categories (:issue:`3472`)
- **Core Bot** - Improved user experience of ``[p]set game/listening/watching/`` commands (:issue:`3562`)
- **Core Bot** - Added ``[p]licenceinfo`` alias for ``[p]licenseinfo`` command to conform with non-American English (:issue:`3460`)
- **Downloader** - Added better logging of errors when Downloader fails to add a repo (:issue:`3558`)
- **Mod** - ``[p]hackban`` and ``[p]unban`` commands support user mentions now (:issue:`3524`)
- **Streams** - Significantly reduce the quota usage for YouTube stream alerts (:issue:`3237`)
- **Warnings** - Users can now pass a reason to ``[p]unwarn`` command (:issue:`3490`, :issue:`3093`)
- **Warnings** - Use more reliant way of checking if command is bot owner only in ``[p]warnaction`` (Warnings cog) (:issue:`3516`, :issue:`3515`)

Fixes
*****

- **Core Bot** - Core cogs will now send bot mention prefix properly in places where discord doesn't render mentions (:issue:`3579`, :issue:`3591`, :issue:`3499`)
- **Core Bot** - Fixed a bug with ``[p]blacklist add`` that made it impossible to blacklist users that bot doesn't share a server with (:issue:`3472`, :issue:`3220`)
- **Core Bot** - Update PyPI domain in ``[p]info`` and update checker (:issue:`3607`)
- **Core Bot** - Stop using deprecated code in Core (:issue:`3610`)
- **Admin** - ``[p]announce`` will now only send error message if an actual errors occurs (:issue:`3514`, :issue:`3513`)
- **Alias** - ``[p]alias help`` will now properly work in non-English locales (:issue:`3546`)
- **Audio** - Users should be able to play age-restricted tracks from YouTube again (:issue:`3620`)
- **Downloader** - Downloader will no longer fail because of invalid ``info.json`` files (:issue:`3533`, :issue:`3456`)
- **Economy** - Next payday time will now be adjusted for users when payday time is changed (:issue:`3496`, :issue:`3438`)
- **Image** - Fixed load error for users that updated Red from version lower than 3.1 to version 3.2 or newer (:issue:`3617`)
- **Streams** - Fixed stream alerts for Twitch (:issue:`3487`)
- **Trivia** - Added better handling for errors in trivia session (:issue:`3606`)
- **Trivia Lists** - Removed empty answers in trivia lists (:issue:`3581`)


Developer changelog
-------------------

Security
********

- Subcommands of command group with ``invoke_without_command=True`` will again inherit this group's checks (:issue:`3614`)

Enhancements
************

- Updated all our dependencies - we're using discord.py 1.3.2 now (:issue:`3609`)
- Added traceback logging to task exception handling (:issue:`3517`)
- Developers can now create a command from an async function wrapped in `functools.partial` (:issue:`3542`)
- Bot will now show deprecation warnings in logs (:issue:`3527`, :issue:`3615`)
- **Downloader** - Downloader will now replace ``[p]`` with clean prefix same as it does in help command (:issue:`3592`)
- **Downloader** - Added schema validation to ``info.json`` file processing - it should now be easier to notice any issues with those files (:issue:`3533`, :issue:`3442`)
- **Utility Functions** - Added clearer error when page is of a wrong type in `redbot.core.utils.menus.menu()` (:issue:`3571`)

Fixes
*****

- **Config** - Fixed Config's singletons (:issue:`3137`, :issue:`3136`)


Documentation changes
---------------------

New Documentation
*****************

- Added guidelines for Cog Creators in `guide_cog_creation` document (:issue:`3568`)

Enhancements
************

- Restructured virtual environment instructions to improve user experience (:issue:`3495`, :issue:`3411`, :issue:`3412`)
- Getting started guide now explains use of quotes for arguments with spaces (:issue:`3555`, :issue:`3111`)
- ``latest`` version of docs now displays a warning about possible differences from current stable release (:issue:`3570`)
- Made systemd guide clearer on obtaining username and python path (:issue:`3537`, :issue:`3462`)
- Improved indication of instructions for different venv types in systemd guide (:issue:`3538`)
- Service file in `autostart_systemd` now also waits for network connection to be ready (:issue:`3549`)
- Hid alias of ``randomize_colour`` in docs (:issue:`3491`)
- Added separate headers for each event predicate class for better navigation (:issue:`3595`, :issue:`3164`)
- Improved wording of explanation for ``required_cogs`` key in `guide_publish_cogs` (:issue:`3520`)


Redbot 3.3.1 (2020-02-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`flyingmongoose`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`palmtree5`, :ghuser:`PredaaA`

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added a cli flag (``--message-cache-size``) for setting a max size of message cache (:issue:`3473`, :issue:`3474`)

Enhancements
************

- **Core Bot** - Prefix can now be edited from command line using ``redbot --edit`` (:issue:`3481`, :issue:`3486`)
- **Core Bot** - Some functions have been changed to no longer use deprecated asyncio functions (:issue:`3509`)
- **Mod** - The short help text for ``[p]modset dm`` has been made more useful (:issue:`3488`)

Fixes
*****

- **Core Bot** - ``[p]dm`` no longer allows owners to have the bot attempt to DM itself (:issue:`3477`, :issue:`3478`)
- **Mod** - Hackban now works properly without being provided a number of days (:issue:`3476`, :issue:`3475`)

Developer changelog
-------------------

Deprecations
************

- **Utility Functions** - Passing the event loop explicitly in `bounded_gather()`, `bounded_gather_iter()`, and `start_adding_reactions()` is deprecated and will be removed in 3.4 (:issue:`3509`)


Documentation changes
---------------------

New Documentation
*****************

- Added section to install docs for CentOS 8 (:issue:`3461`, :issue:`3463`)

Enhancements
************

- Added ``-e`` flag to ``journalctl`` command in systemd guide so that it takes the user to the end of logs automatically (:issue:`3483`)
- Improved usage of apt update in docs (:issue:`3464`)

Redbot 3.3.0 (2020-01-26)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`DevilXD`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`Stonedestroyer`, :ghuser:`zephyrkul`

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Team applications are now supported (:issue:`2781`, :issue:`3445`)

    - Added new ``--team-members-are-owners`` flag that will make Red treat owners of the team application as bot owners
- **Core Bot** - Embed use can now be configured per channel with new ``[p]embedset channel`` command (:issue:`3152`, :issue:`3418`)
- **Mod** - You can set a default amount of days to clean up when banning with ``[p]ban`` and ``[p]tempban`` (:issue:`2441`, :issue:`2930`, :issue:`3437`)
- **Mod** - Users can now optionally be DMed their ban reason (:issue:`2649`, :issue:2990`)

Enhancements
************

- **Core Bot** - The commands module has been slightly restructured to provide more useful data to developers (:issue:`3410`)
- **Core Bot** - Help is now self consistent in the extra formatting used (:issue:`3451`)
- **Admin** - Role granting/removing commands will now notify when the user already has/doesn't have a role when attempting to add/remove it (:issue:`3010`, :issue:`3408`)
- **Audio** - Playlist searching is now more intuitive (:issue:`3430`)
- **Downloader** - Some user facing messages were improved (:issue:`3409`)
- **Mod** - ``[p]slowmode`` should no longer error on nonsensical time quantities (:issue:`3453`)

Fixes
*****

- **Audio** - ``[p]audioset dc`` and ``[p]repeat`` commands no longer interfere with each other (:issue:`3425`, :issue:`3426`)
- **Cleanup** - Fixed a rare edge case involving messages that were deleted during cleanup (:issue:`3414`)
- **CustomCommands** - ``[p]cc create random`` no longer errors when exiting an interactive menu (:issue:`3416`, :issue:`3417`)
- **Downloader** - Downloader's initialization can no longer time out at startup (:issue:`3415`, :issue:`3440`, :issue:`3444`)
- **General** - ``[p]roll`` command will no longer attempt to roll obscenely large amounts (:issue:`3284`, :issue:`3395`)
- **Permissions** - Now has stronger enforcement of prioritizing botwide settings

Developer changelog
-------------------

Breaking Changes
****************

- Importing submodules of ``discord.ext.commands`` from ``redbot.core.commands`` will no longer work (:issue:`3410`)
- ``PermState.ALLOWED_STATES`` from ``redbot.core.commands.requires`` has been moved to a global variable called ``PermStateAllowedStates`` in the same module (:issue:`3410`)
- ``PermState.TRANSITIONS`` from ``redbot.core.commands.requires`` has been moved to a global variable called ``PermStateAllowedStates`` in the same module (:issue:`3410`)
- Use of ``@asyncio.coroutine`` is no longer supported. Use ``async def`` instead (:issue:`3410`)

Enhancements
************

- We now use discord.py 1.3.1 (:issue:`3445`)

Deprecations
************

- **Downloader** - Updated deprecation warnings for shared libs to reflect that they will instead be removed in 3.4 (:issue:`3449`)

Fixes
*****

- Fixed an issue with default units in `TimedeltaConverter` (:issue:`3453`)


Documentation Changes
---------------------

Fixes
*****

- We've made some small fixes to inaccurate instructions about installing with pyenv (:issue:`3434`)


Redbot 3.2.3 (2020-01-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`Redjumpman`, :ghuser:`Stonedestroyer`, :ghuser:`TrustyJAID`

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - The bot's description is now configurable (:issue:`3340`)
- **Core Bot** - Added the means for cog creators to use a global preinvoke hook (:issue:`3369`)

Enhancements
************

- **Core Bot** - Further improvements have been made to bot startup and shutdown (:issue:`3358`, :issue:`3392`)
- **Core Bot** - Prefixes are now cached for performance (:issue:`3148`, :issue:`3150`)
- **Core Bot** - The bot now ensures it has at least the bare neccessary permissions before running commands (:issue:`3304`, :issue:`3305`, :issue:`3361`)
- **Core Bot** - The ``[p]servers`` command now also shows the ids (:issue:`3224`, :issue:`3393`)
- **Audio** - Reduced cooldowns for some of the playlist commands (:issue:`3342`)
- **Downloader** - Improved a few user facing messages (:issue:`3343`)
- **Downloader** - Added logging of failures (:issue:`3372`)

Fixes
*****

- **Core Bot** - Deleting instances works as intended again (:issue:`3338`, :issue:`3384`)
- **Core Bot** - Embed settings (``[p]embedset``) for ``[p]help`` now work the same as for other commands (:issue:`3382`)
- **Admin** - The selfrole command now has reasonable expectations about hierarchy  (:issue:`3331`)
- **Audio** - Audio now properly disconnects the bot when ``[p]audioset dc`` is turned on, even if ``[p]audioset notify`` is being used (:issue:`3349`, :issue:`3350`)
- **Audio** - Symbolic links now work as intended for local tracks (:issue:`3332`, :issue:`3376`)
- **Audio** - ``[p]bumpplay`` now shows the correct remaining time until the bumped track is played (:issue:`3373`, :issue:`3375`)
- **Audio** - Multiple user facing messages have been made more correct (:issue:`3347`, :issue:`3348`, :issue:`3374`)
- **Downloader** - Added pagination of output on cog update when it's too long for single message (:issue:`3385`, :issue:`3388`)


Developer changelog
-------------------

New Functionality
*****************

- ``[botname]`` is now replaced with the bot's display name in help text (:issue:`3339`)
- New features added for cog creators to further customize help behavior (:issue:`3339`)
  
  - Check out our command reference for details on new ``format_help_for_context`` method


Documentation changes
---------------------

New Documentation
*****************

- Added proper support for Ubuntu non-LTS (:issue:`3330`, :issue:`3336`)
- Added link to our GitHub in the documentation (:issue:`3306`)

Enhancements
************

- Added a note about how to update Red to the install guides (:issue:`3400`)
- Clarified some information about breaking changes in Red 3.2.0 changelog (:issue:`3367`)
- Improved the structure of the Linux/Mac install guide to make it more clear to the user which sections they should be following (:issue:`3365`)
- Added more details to the API key reference (:issue:`3400`)
- Updated the documentation to **require** the usage of virtual environment for installing and running Red (:issue:`3351`)
- Updated auto-restart guides to use Python's ``-O`` flag to enable assert optimizations (:issue:`3354`)

Fixes
*****

- Updated the documentation with the minimum supported git version (:issue:`3371`)
- Fixed install instructions for Debian to also work with Debian Stretch (:issue:`3352`)


Redbot 3.2.2 (2020-01-10)
=========================

End-user changelog
------------------

Fixes
*****

- **Core Bot** - Fixed pagination issue in ``[p]help`` command (:issue:`3323`, :issue:`3324`)

Documentation changes
---------------------

Fixes
*****

- Corrected venv docs to use the actually supported Python version (:issue:`3325`, :issue:`3324`)


Redbot 3.2.1 (2020-01-10)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`mikeshardmind`, :ghuser:`palmtree5`

End-user changelog
------------------

Enhancements
************

- **Modlog** - Modlog will now log an error with unexpected case type key (and any other keys) rather than crash (:issue:`3318`)

Fixes
*****

- **Core Bot** - Fixed Mongo conversion from being incorrectly blocked (:issue:`3316`, :issue:`3319`)
- **Admin** - Fixed announcer not creating a message for success feedback (:issue:`3320`)


Redbot 3.2.0 (2020-01-09)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Aurorum`, :ghuser:`Bakersbakebread`, :ghuser:`DevilXD`, :ghuser:`DiscordLiz`, :ghuser:`DJtheRedstoner`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`jerbob`, :ghuser:`jonasbohmann`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`RealFriesi`, :ghuser:`retke`, :ghuser:`Tobotimus`, :ghuser:`Vexed01`, :ghuser:`wereii`, :ghuser:`yamikaitou`, :ghuser:`ZeLarpMaster`, :ghuser:`zephyrkul`

Core Bot Changes
----------------

Breaking Changes
****************

- Modlog casetypes no longer have an attribute for auditlog action type. (:issue:`2897`)
- Removed ``redbot.core.modlog.get_next_case_number()``. (:issue:`2908`)
- Removed ``bank.MAX_BALANCE``, use ``bank.get_max_balance()`` from now on. (:issue:`2926`)
- The main bot config is no longer directly accessible to cogs. New methods have been added for use where this is concerned.
  New methods for this include

    - ``bot.get_shared_api_tokens``
    - ``bot.set_shared_api_tokens``
    - ``bot.get_embed_color``
    - ``bot.get_embed_colour``
    - ``bot.get_admin_roles``
    - ``bot.get_admin_role_ids``
    - ``bot.get_mod_roles``
    - ``bot.get_mod_role_ids`` (:issue:`2967`)
- Reserved some command names for internal Red use. These are available programatically as ``redbot.core.commands.RESERVED_COMMAND_NAMES``. (:issue:`2973`)
- Removed ``bot._counter``, Made a few more attrs private (``cog_mgr``, ``main_dir``). (:issue:`2976`)
- Extension's ``setup()`` function should no longer assume that we are, or even will be connected to Discord.
  This also means that cog creators should no longer use ``bot.wait_until_ready()`` inside it. (:issue:`3073`)
- Removed the mongo driver. (:issue:`3099`)


Bug Fixes
*********

- Help now properly hides disabled commands. (:issue:`2863`)
- Fixed ``bot.remove_command`` throwing an error when trying to remove a non-existent command. (:issue:`2888`)
- ``Command.can_see`` now works as intended for disabled commands. (:issue:`2892`)
- Modlog entries now show up properly without the mod cog loaded. (:issue:`2897`)
- Fixed an error in ``[p]reason`` when setting the reason for a case without a moderator. (:issue:`2908`)
- Bank functions now check the recipient balance before transferring and stop the transfer if the recipient's balance will go above the maximum allowed balance. (:issue:`2923`)
- Removed potential for additional bad API calls per ban/unban. (:issue:`2945`)
- The ``[p]invite`` command no longer errors when a user has the bot blocked or DMs disabled in the server. (:issue:`2948`)
- Stopped using the ``:`` character in backup's filename - Windows doesn't accept it. (:issue:`2954`)
- ``redbot-setup delete`` no longer errors with "unexpected keyword argument". (:issue:`2955`)
- ``redbot-setup delete`` no longer prompts about backup when the user passes the option ``--no-prompt``. (:issue:`2956`)
- Cleaned up the ``[p]inviteset public`` and ``[p]inviteset perms`` help strings.  (:issue:`2963`)
- ```[p]embedset user`` now only affects DM's. (:issue:`2966`)
- Fixed an unfriendly error when the provided instance name doesn't exist. (:issue:`2968`)
- Fixed the help text and response of ``[p]set usebotcolor`` to accurately reflect what the command is doing. (:issue:`2974`)
- Red no longer types infinitely when a command with a cooldown is called within the last second of a cooldown. (:issue:`2985`)
- Removed f-string usage in the launcher to prevent our error handling from causing an error. (:issue:`3002`)
- Fixed ``MessagePredicate.greater`` and ``MessagePredicate.less`` allowing any valid int instead of only valid ints/floats that are greater/less than the given value. (:issue:`3004`)
- Fixed an error in ``[p]uptime`` when the uptime is under a second. (:issue:`3009`)
- Added quotation marks to the response of ``[p]helpset tagline`` so that two consecutive full stops do not appear. (:issue:`3010`)
- Fixed an issue with clearing rules in permissions. (:issue:`3014`)
- Lavalink will now be restarted after an unexpected shutdown. (:issue:`3033`)
- Added a 3rd-party lib folder to ``sys.path`` before loading cogs. This prevents issues with 3rd-party cogs failing to load when Downloader is not loaded to install requirements. (:issue:`3036`)
- Escaped track descriptions so that they do not break markdown. (:issue:`3047`)
- Red will now properly send a message when the invoked command is guild-only. (:issue:`3057`)
- Arguments ``--co-owner`` and ``--load-cogs`` now properly require at least one argument to be passed. (:issue:`3060`)
- Now always appends the 3rd-party lib folder to the end of ``sys.path`` to avoid shadowing Red's dependencies. (:issue:`3062`)
- Fixed ``is_automod_immune``'s handling of the guild check and added support for checking webhooks. (:issue:`3100`)
- Fixed the generation of the ``repos.json`` file in the backup process. (:issue:`3114`)
- Fixed an issue where calling audio commands when not in a voice channel could result in a crash. (:issue:`3120`)
- Added handling for invalid folder names in the data path gracefully in ``redbot-setup`` and ``redbot --edit``. (:issue:`3171`)
- ``--owner`` and ``-p`` cli flags now work when added from launcher. (:issue:`3174`)
- Red will now prevent users from locking themselves out with localblacklist. (:issue:`3207`)
- Fixed help ending up a little too large for discord embed limits. (:issue:`3208`)
- Fixed formatting issues in commands that list whitelisted/blacklisted users/roles when the list is empty. (:issue:`3219`)
- Red will now prevent users from locking the guild owner out with localblacklist (unless the command caller is bot owner). (:issue:`3221`)
- Guild owners are no longer affected by the local whitelist and blacklist. (:issue:`3221`)
- Fixed an attribute error that can be raised in ``humanize_timedelta`` if ``seconds = 0``. (:issue:`3231`)
- Fixed ``ctx.clean_prefix`` issues resulting from undocumented changes from discord. (:issue:`3249`)
- ``redbot.core.bot.Bot.owner_id`` is now set in the post connection startup. (:issue:`3273`)
- ``redbot.core.bot.Bot.send_to_owners()`` and ``redbot.core.bot.Bot.get_owner_notification_destinations()`` now wait until Red is done with post connection startup to ensure owner ID is available. (:issue:`3273`)


Enhancements
************

- Added the option to modify the RPC port with the ``--rpc-port`` flag. (:issue:`2429`)
- Slots now has a 62.5% expected payout and will not inflate economy when spammed. (:issue:`2875`)
- Allowed passing ``cls`` in the ``redbot.core.commands.group()`` decorator. (:issue:`2881`)
- Red's Help Formatter is now considered to have a stable API. (:issue:`2892`)
- Modlog no longer generates cases without being told to for actions the bot did. (:issue:`2897`)
- Some generic modlog casetypes are now pre-registered for cog creator use. (:issue:`2897`)
- ModLog is now much faster at creating cases, especially in large servers. (:issue:`2908`)
- JSON config files are now stored without indentation, this is to reduce the file size and increase the performance of write operations. (:issue:`2921`)
- ``--[no-]backup``, ``--[no-]drop-db`` and ``--[no-]remove-datapath`` in the ``redbot-setup delete`` command are now on/off flags. (:issue:`2958`)
- The confirmation prompts in ``redbot-setup`` now have default values for user convenience. (:issue:`2958`)
- ``redbot-setup delete`` now has the option to leave Red's data untouched on database backends. (:issue:`2962`)
- Red now takes less time to fetch cases, unban members, and list warnings. (:issue:`2964`)
- Red now handles more things prior to connecting to discord to reduce issues during the initial load. (:issue:`3045`)
- ``bot.send_filtered`` now returns the message that is sent. (:issue:`3052`)
- Red will now send a message when the invoked command is DM-only. (:issue:`3057`)
- All ``y/n`` confirmations in cli commands are now unified. (:issue:`3060`)
- Changed ``[p]info`` to say "This bot is an..." instead of "This is an..." for clarity. (:issue:`3121`)
- ``redbot-setup`` will now use the instance name in default data paths to avoid creating a second instance with the same data path. (:issue:`3171`)
- Instance names can now only include characters A-z, numbers, underscores, and hyphens. Old instances are unaffected by this change. (:issue:`3171`)
- Clarified that ``[p]backup`` saves the **bot's** data in the help text. (:issue:`3172`)
- Added ``redbot --debuginfo`` flag which shows useful information for debugging. (:issue:`3183`)
- Added the Python executable field to ``[p]debuginfo``. (:issue:`3184`)
- When Red prompts for a token, it will now print a link to the guide explaining how to obtain a token. (:issue:`3204`)
- ``redbot-setup`` will no longer log to disk. (:issue:`3269`)
- ``redbot.core.bot.Bot.send_to_owners()`` and ``redbot.core.bot.Bot.get_owner_notification_destinations()`` now log when they are not able to find the owner notification destination. (:issue:`3273`)
- The lib folder is now cleared on minor Python version changes. ``[p]cog reinstallreqs`` in Downloader can be used to regenerate the lib folder for a new Python version. (:issue:`3274`)
- If Red detects operating system or architecture change, it will now warn the owner about possible problems with the lib folder. (:issue:`3274`)
- ``[p]playlist download`` will now compress playlists larger than the server attachment limit and attempt to send that. (:issue:`3279`)


New Features
************

- Added functions to acquire locks on Config groups and values. These locks are acquired by default when calling a value as a context manager. See ``Value.get_lock`` for details. (:issue:`2654`)
- Added a config driver for PostgreSQL. (:issue:`2723`)
- Added methods to Config for accessing things by id without mocked objects

    - ``Config.guild_from_id``
    - ``Config.user_from_id``
    - ``Config.role_from_id``
    - ``Config.channel_from_id``
    - ``Config.member_from_ids``
      - This one requires multiple ids, one for the guild, one for the user
      - Consequence of discord's object model (:issue:`2804`)
- New method ``humanize_number`` in ``redbot.core.utils.chat_formatting`` to convert numbers into text that respects the current locale. (:issue:`2836`)
- Added new commands to Economy

  - ``[p]bank prune user`` - This will delete a user's bank account.
  - ``[p]bank prune local`` - This will prune the bank of accounts for users who are no longer in the server.
  - ``[p]bank prune global`` - This will prune the global bank of accounts for users who do not share any servers with the bot. (:issue:`2845`)
- Red now uses towncrier for changelog generation. (:issue:`2872`)
- Added ``redbot.core.modlog.get_latest_case`` to fetch the case object for the most recent ModLog case. (:issue:`2908`)
- Added ``[p]bankset maxbal`` to set the maximum bank balance. (:issue:`2926`)
- Added a few methods and classes replacing direct config access (which is no longer supported)

   - ``redbot.core.Red.allowed_by_whitelist_blacklist``
   - ``redbot.core.Red.get_valid_prefixes``
   - ``redbot.core.Red.clear_shared_api_tokens``
   - ``redbot.core.commands.help.HelpSettings`` (:issue:`2976`)
- Added the cli flag ``redbot --edit`` which is used to edit the instance name, token, owner, and datapath. (:issue:`3060`)
- Added ``[p]licenseinfo``. (:issue:`3090`)
- Ensured that people can migrate from MongoDB. (:issue:`3108`)
- Added a command to list disabled commands globally or per guild. (:issue:`3118`)
- New event ``on_red_api_tokens_update`` is now dispatched when shared api keys for a service are updated. (:issue:`3134`)
- Added ``redbot-setup backup``. (:issue:`3235`)
- Added the method ``redbot.core.bot.Bot.wait_until_red_ready()`` that waits until Red's post connection startup is done. (:issue:`3273`)


Removals
********

- ``[p]set owner`` and ``[p]set token`` have been removed in favor of managing server side. (:issue:`2928`)
- Shared libraries are marked for removal in Red 3.4. (:issue:`3106`)
- Removed ``[p]backup``. Use the cli command ``redbot-setup backup`` instead. (:issue:`3235`)
- Removed the functions ``safe_delete``, ``fuzzy_command_search``, ``format_fuzzy_results`` and ``create_backup`` from ``redbot.core.utils``. (:issue:`3240`)
- Removed a lot of the launcher's handled behavior. (:issue:`3289`)


Miscellaneous changes
*********************

- :issue:`2527`, :issue:`2571`, :issue:`2723`, :issue:`2836`, :issue:`2849`, :issue:`2861`, :issue:`2885`, :issue:`2890`, :issue:`2897`, :issue:`2904`, :issue:`2924`, :issue:`2939`, :issue:`2940`, :issue:`2941`, :issue:`2949`, :issue:`2953`, :issue:`2964`, :issue:`2986`, :issue:`2993`, :issue:`2997`, :issue:`3008`, :issue:`3017`, :issue:`3048`, :issue:`3059`, :issue:`3080`, :issue:`3089`, :issue:`3104`, :issue:`3106`, :issue:`3129`, :issue:`3152`, :issue:`3160`, :issue:`3168`, :issue:`3173`, :issue:`3176`, :issue:`3186`, :issue:`3192`, :issue:`3193`, :issue:`3195`, :issue:`3202`, :issue:`3214`, :issue:`3223`, :issue:`3229`, :issue:`3245`, :issue:`3247`, :issue:`3248`, :issue:`3250`, :issue:`3254`, :issue:`3255`, :issue:`3256`, :issue:`3258`, :issue:`3261`, :issue:`3275`, :issue:`3276`, :issue:`3293`, :issue:`3278`, :issue:`3285`, :issue:`3296`,


Dependency changes
***********************

- Added ``pytest-mock`` requirement to ``tests`` extra. (:issue:`2571`)
- Updated the python minimum requirement to 3.8.1, updated JRE to Java 11. (:issue:`3245`)
- Bumped dependency versions. (:issue:`3288`)
- Bumped red-lavalink version. (:issue:`3290`)


Documentation Changes
*********************

- Started the user guides covering cogs and the user interface of the bot. This includes, for now, a "Getting started" guide. (:issue:`1734`)
- Added documentation for PM2 support. (:issue:`2105`)
- Updated linux install docs, adding sections for Fedora Linux, Debian/Raspbian Buster, and openSUSE. (:issue:`2558`)
- Created documentation covering what we consider a developer facing breaking change and the guarantees regarding them. (:issue:`2882`)
- Fixed the user parameter being labeled as ``discord.TextChannel`` instead of ``discord.abc.User`` in ``redbot.core.utils.predicates``. (:issue:`2914`)
- Updated towncrier info in the contribution guidelines to explain how to create a changelog for a standalone PR. (:issue:`2915`)
- Reworded the virtual environment guide to make it sound less scary. (:issue:`2920`)
- Driver docs no longer show twice. (:issue:`2972`)
- Added more information about ``redbot.core.utils.humanize_timedelta`` into the docs. (:issue:`2986`)
- Added a direct link to the "Installing Red" section in "Installing using powershell and chocolatey". (:issue:`2995`)
- Updated Git PATH install (Windows), capitalized some words, stopped mentioning the launcher. (:issue:`2998`)
- Added autostart documentation for Red users who installed Red inside of a virtual environment. (:issue:`3005`)
- Updated the Cog Creation guide with a note regarding the Develop version as well as the folder layout for local cogs. (:issue:`3021`)
- Added links to the getting started guide at the end of installation guides. (:issue:`3025`)
- Added proper docstrings to enums that show in drivers docs. (:issue:`3035`)
- Discord.py doc links will now always use the docs for the currently used version of discord.py. (:issue:`3053`)
- Added ``|DPY_VERSION|`` substitution that will automatically get replaced by the current discord.py version. (:issue:`3053`)
- Added missing descriptions for function returns. (:issue:`3054`)
- Stopped overwriting the ``docs/prolog.txt`` file in ``conf.py``. (:issue:`3082`)
- Fixed some typos and wording, added MS Azure to the host list. (:issue:`3083`)
- Updated the docs footer copyright to 2019. (:issue:`3105`)
- Added a deprecation note about shared libraries in the Downloader Framework docs. (:issue:`3106`)
- Updated the apikey framework documentation. Changed ``bot.get_shared_api_keys()`` to ``bot.get_shared_api_tokens()``. (:issue:`3110`)
- Added information about ``info.json``'s ``min_python_version`` key in Downloader Framework docs. (:issue:`3124`)
- Added an event reference for the ``on_red_api_tokens_update`` event in the Shared API Keys docs. (:issue:`3134`)
- Added notes explaining the best practices with config. (:issue:`3149`)
- Documented additional attributes in Context. (:issue:`3151`)
- Updated Windows docs with up to date dependency instructions. (:issue:`3188`)
- Added a "Publishing cogs for V3" document explaining how to make user's cogs work with Downloader. (:issue:`3234`)
- Fixed broken docs for ``redbot.core.commands.Context.react_quietly``. (:issue:`3257`)
- Updated copyright notices on License and RTD config to 2020. (:issue:`3259`)
- Added a line about setuptools and wheel. (:issue:`3262`)
- Ensured development builds are not advertised to the wrong audience. (:issue:`3292`)
- Clarified the usage intent of some of the chat formatting functions. (:issue:`3292`)


Admin
-----

Breaking Changes
****************

- Changed ``[p]announce ignore`` and ``[p]announce channel`` to ``[p]announceset ignore`` and ``[p]announceset channel``. (:issue:`3250`)
- Changed ``[p]selfrole <role>`` to ``[p]selfrole add <role>``, changed ``[p]selfrole add`` to ``[p]selfroleset add`` , and changed ``[p]selfrole delete`` to ``[p]selfroleset remove``. (:issue:`3250`)


Bug Fixes
*********

- Fixed ``[p]announce`` failing after encountering an error attempting to message the bot owner. (:issue:`3166`)
- Improved the clarity of user facing messages when the user is not allowed to do something due to Discord hierarchy rules. (:issue:`3250`)
- Fixed some role managing commands not properly checking if Red had ``manage_roles`` perms before attempting to manage roles. (:issue:`3250`)
- Fixed ``[p]editrole`` commands not checking if roles to be edited are higher than Red's highest role before trying to edit them. (:issue:`3250`)
- Fixed ``[p]announce ignore`` and ``[p]announce channel`` not being able to be used by guild owners and administrators. (:issue:`3250`)


Enhancements
************

- Added custom issue messages for adding and removing roles, this makes it easier to create translations. (:issue:`3016`)


Audio
-----

Bug Fixes
*********

- ``[p]playlist remove`` now removes the playlist url if the playlist was created through ``[p]playlist save``. (:issue:`2861`)
- Users are no longer able to accidentally overwrite existing playlist if a new one with the same name is created/renamed. (:issue:`2861`)
- ``[p]audioset settings`` no longer shows lavalink JAR version. (:issue:`2904`)
- Fixed a ``KeyError: loadType`` when trying to play tracks. (:issue:`2904`)
- ``[p]audioset settings`` now uses ``ctx.is_owner()`` to check if the context author is the bot owner. (:issue:`2904`)
- Fixed track indexs being off by 1 in ``[p]search``. (:issue:`2940`)
- Fixed an issue where updating your Spotify and YouTube Data API tokens did not refresh them. (:issue:`3047`)
- Fixed an issue where the blacklist was not being applied correctly. (:issue:`3047`)
- Fixed an issue in ``[p]audioset restrictions blacklist list`` where it would call the list a ``Whitelist``. (:issue:`3047`)
- Red's status is now properly cleared on emptydisconnect. (:issue:`3050`)
- Fixed a console spam caused sometimes when auto disconnect and auto pause are used. (:issue:`3123`)
- Fixed an error that was thrown when running ``[p]audioset dj``. (:issue:`3165`)
- Fixed a crash that could happen when the bot can't connect to the lavalink node. (:issue:`3238`)
- Restricted the number of songs shown in the queue to first 500 to avoid heartbeats. (:issue:`3279`)
- Added more cooldowns to playlist commands and restricted the queue and playlists to 10k songs to avoid bot errors. (:issue:`3286`)


Enhancements
************

- ``[p]playlist upload`` will now load playlists generated via ``[p]playlist download`` much faster if the playlist uses the new scheme. (:issue:`2861`)
- ``[p]playlist`` commands now can be used by everyone regardless of DJ settings, however it will respect DJ settings when creating/modifying playlists in the server scope. (:issue:`2861`)
- Spotify, Youtube Data, and Lavalink API calls can be cached to avoid repeated calls in the future, see ``[p]audioset cache``. (:issue:`2890`)
- Playlists will now start playing as soon as first track is loaded. (:issue:`2890`)
- ``[p]audioset localpath`` can set a path anywhere in your machine now. Note: This path needs to be visible by ``Lavalink.jar``. (:issue:`2904`)
- ``[p]queue`` now works when there are no tracks in the queue, showing the track currently playing. (:issue:`2904`)
- ``[p]audioset settings`` now reports Red Lavalink version. (:issue:`2904`)
- Adding and removing reactions in Audio is no longer a blocking action. (:issue:`2904`)
- When shuffle is on, queue now shows the correct play order. (:issue:`2904`)
- ``[p]seek`` and ``[p]skip`` can be used by user if they are the song requester while DJ mode is enabled and votes are disabled. (:issue:`2904`)
- Adding a playlist and an album to a saved playlist skips tracks already in the playlist. (:issue:`2904`)
- DJ mode is now turned off if the DJ role is deleted. (:issue:`2904`)
- When playing a localtrack, ``[p]play`` and ``[p]bumpplay`` no longer require the use of the prefix "localtracks\\".

  Before: ``[p]bumpplay localtracks\\ENM\\501 - Inside The Machine.mp3``
  Now: ``[p]bumpplay ENM\\501 - Inside The Machine.mp3``
  Now nested folders: ``[p]bumpplay Parent Folder\\Nested Folder\\track.mp3`` (:issue:`2904`)
- Removed commas in explanations about how to set API keys. (:issue:`2905`)
- Expanded local track support to all file formats (m3u, m4a, mp4, etc). (:issue:`2940`)
- Cooldowns are now reset upon failure of commands that have a cooldown timer. (:issue:`2940`)
- Improved the explanation in the help string for ``[p]audioset emptydisconnect``. (:issue:`3051`)
- Added a typing indicator to playlist dedupe. (:issue:`3058`)
- Exposed clearer errors to users in the play commands. (:issue:`3085`)
- Better error handling when the player is unable to play multiple tracks in the sequence. (:issue:`3165`)


New Features
************

- Added support for nested folders in the localtrack folder. (:issue:`270`)
- Now auto pauses the queue when the voice channel is empty. (:issue:`721`)
- All Playlist commands now accept optional arguments, use ``[p]help playlist <subcommand>`` for more details. (:issue:`2861`)
- ``[p]playlist rename`` will now allow users to rename existing playlists. (:issue:`2861`)
- ``[p]playlist update`` will now allow users to update non-custom Playlists to the latest available tracks. (:issue:`2861`)
- There are now 3 different scopes of playlist. To define them, use the ``--scope`` argument.

      ``Global Playlist``

      - These playlists will be available in all servers the bot is in.
      - These can be managed by the Bot Owner only.

      ``Server Playlist``

      - These playlists will only be available in the server they were created in.
      - These can be managed by the Bot Owner, Guild Owner, Mods, Admins, DJs, and the Creator (if the DJ role is disabled).

      ``User Playlist``

      - These playlists will be available in all servers both the bot and the creator are in.
      - These can be managed by the Bot Owner and Creator only. (:issue:`2861`)
- ``[p]audioset cache`` can be used to set the cache level. **It's off by default**. (:issue:`2904`)
- ``[p]genre`` can be used to play spotify playlists. (:issue:`2904`)
- ``[p]audioset cacheage`` can be used to set the maximum age of an entry in the cache. **Default is 365 days**. (:issue:`2904`)
- ``[p]audioset autoplay`` can be used to enable auto play once the queue runs out. (:issue:`2904`)
- New events dispatched by Audio.

   - ``on_red_audio_track_start(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_enqueue(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_auto_play(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_queue_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_audio_disconnect(guild: discord.Guild)``
   - ``on_red_audio_skip_track(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)`` (:issue:`2904`)
- ``[p]queue shuffle`` can be used to shuffle the queue manually. (:issue:`2904`)
- ``[p]queue clean self`` can be used to remove all songs you requested from the queue. (:issue:`2904`)
- ``[p]audioset restrictions`` can be used to add or remove keywords which songs must have or are not allowed to have. (:issue:`2904`)
- ``[p]playlist dedupe`` can be used to remove duplicated tracks from a playlist. (:issue:`2904`)
- ``[p]autoplay`` can be used to play a random song. (:issue:`2904`)
- ``[p]bumpplay`` can be used to add a song to the front of the queue. (:issue:`2940`)
- ``[p]shuffle`` has an additional argument to tell the bot whether it should shuffle bumped tracks. (:issue:`2940`)
- Added global whitelist/blacklist commands. (:issue:`3047`)
- Added self-managed daily playlists in the GUILD scope, these are called "Daily playlist - YYYY-MM-DD" and auto delete after 7 days. (:issue:`3199`)


CustomCom
---------

Enhancements
************

- The group command ``[p]cc create`` can now be used to create simple CCs without specifying "simple". (:issue:`1767`)
- Added a query option for CC typehints for URL-based CCs. (:issue:`3228`)
- Now uses the ``humanize_list`` utility for iterable parameter results, e.g. ``{#:Role.members}``. (:issue:`3277`)


Downloader
----------

Bug Fixes
*********

- Made the regex for repo names use raw strings to stop causing a ``DeprecationWarning`` for invalid escape sequences. (:issue:`2571`)
- Downloader will no longer attempt to install cogs that are already installed. (:issue:`2571`)
- Repo names can now only contain the characters listed in the help text (A-Z, 0-9, underscores, and hyphens). (:issue:`2827`)
- ``[p]findcog`` no longer attempts to find a cog for commands without a cog. (:issue:`2902`)
- Downloader will no longer attempt to install a cog with same name as another cog that is already installed. (:issue:`2927`)
- Added error handling for when a remote repository or branch is deleted, now notifies the which repository failed and continues to update the others. (:issue:`2936`)
- ``[p]cog install`` will no longer error if a cog has an empty install message. (:issue:`3024`)
- Made ``redbot.cogs.downloader.repo_manager.Repo.clean_url`` work with relative urls. This property is ``str`` type now. (:issue:`3141`)
- Fixed an error on repo add from empty string values for the ``install_msg`` info.json field. (:issue:`3153`)
- Disabled all git auth prompts when adding/updating a repo with Downloader. (:issue:`3159`)
- ``[p]findcog`` now properly works for cogs with less typical folder structure. (:issue:`3177`)
- ``[p]cog uninstall`` now fully unloads cog - the bot will not try to load it on next startup. (:issue:`3179`)


Enhancements
************

- Downloader will now check if the Python and bot versions match requirements in ``info.json`` during update. (:issue:`1866`)
- ``[p]cog install`` now accepts multiple cog names. (:issue:`2527`)
- When passing cogs to ``[p]cog update``, it will now only update those cogs, not all cogs from the repo those cogs are from. (:issue:`2527`)
- Added error messages for failures when installing/reinstalling requirements and copying cogs and shared libraries. (:issue:`2571`)
- ``[p]findcog`` now uses sanitized urls (without HTTP Basic Auth fragments). (:issue:`3129`)
- ``[p]repo info`` will now show the repo's url, branch, and authors. (:issue:`3225`)
- ``[p]cog info`` will now show cog authors. (:issue:`3225`)
- ``[p]findcog`` will now show the repo's branch. (:issue:`3225`)


New Features
************

- Added ``[p]repo update [repos]`` which updates repos without updating the cogs from them. (:issue:`2527`)
- Added ``[p]cog installversion <repo_name> <revision> <cogs>`` which installs cogs from a specified revision (commit, tag) of the given repo. When using this command, the cog will automatically be pinned. (:issue:`2527`)
- Added ``[p]cog pin <cogs>`` and ``[p]cog unpin <cogs>`` for pinning cogs. Cogs that are pinned will not be updated when using update commands. (:issue:`2527`)
- Added ``[p]cog checkforupdates`` that lists which cogs can be updated (including pinned cog) without updating them. (:issue:`2527`)
- Added ``[p]cog updateallfromrepos <repos>`` that updates all cogs from the given repos. (:issue:`2527`)
- Added ``[p]cog updatetoversion <repo_name> <revision> [cogs]`` that updates all cogs or ones of user's choosing to chosen revision of the given repo. (:issue:`2527`)
- Added ``[p]cog reinstallreqs`` that reinstalls cog requirements and shared libraries for all installed cogs. (:issue:`3167`)


Documentation Changes
*********************

- Added ``redbot.cogs.downloader.installable.InstalledModule`` to Downloader's framework docs. (:issue:`2527`)
- Removed API References for Downloader. (:issue:`3234`)


Image
-----

Enhancements
************

- Updated the giphycreds command to match the formatting of the other API commands. (:issue:`2905`)
- Removed commas from explanations about how to set API keys. (:issue:`2905`)


Mod
---

Bug Fixes
*********

- ``[p]userinfo`` no longer breaks when a user has an absurd numbers of roles. (:issue:`2910`)
- Fixed Mod cog not recording username changes for ``[p]names`` and ``[p]userinfo`` commands. (:issue:`2918`)
- Fixed ``[p]modset deletedelay`` deleting non-command messages. (:issue:`2924`)
- Fixed an error when reloading Mod. (:issue:`2932`)


Enhancements
************

- Slowmode now accepts integer-only inputs as seconds. (:issue:`2884`)


Permissions
-----------

Bug Fixes
*********

- Defaults are now cleared properly when clearing all rules. (:issue:`3037`)


Enhancements
************

- Better explained the usage of commands with the ``<who_or_what>`` argument. (:issue:`2991`)


Streams
-------

Bug Fixes
*********

- Fixed a ``TypeError`` in the ``TwitchStream`` class when calling Twitch client_id from Red shared APIs tokens. (:issue:`3042`)
- Changed the ``stream_alert`` function for Twitch alerts to make it work with how the ``TwitchStream`` class works now. (:issue:`3042`)


Enhancements
************

- Removed commas from explanations about how to set API keys. (:issue:`2905`)


Trivia
------

Bug Fixes
*********

- Fixed a typo in Ahsoka Tano's name in the Starwars trivia list. (:issue:`2909`)
- Fixed a bug where ``[p]trivia leaderboard`` failed to run. (:issue:`2911`)
- Fixed a typo in the Greek mythology trivia list regarding Hermes' staff. (:issue:`2994`)
- Fixed a question in the Overwatch trivia list that accepted blank responses. (:issue:`2996`)
- Fixed questions and answers that were incorrect in the Clash Royale trivia list. (:issue:`3236`)


Enhancements
************

- Added trivia lists for Prince and Michael Jackson lyrics. (:issue:`12`)


Redbot 3.1.9 (2020-01-08)
=========================

This is a maintenance release patching a denial of service issue with Audio.


Redbot 3.1.8 (2019-11-19)
=========================

This is a hotfix release updating discord.py to fix a full bot crash when emoji reaction is added/removed.
This was caused by Discord API changes.


Redbot 3.1.7 (2019-11-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`mikeshardmind`

End-user changelog
------------------

Enhancements
************

- Improved handling of user facing errors (`989e16b <https://github.com/Cog-Creators/Red-DiscordBot/commit/989e16b20b814971e01a8657dedf4d9b45c23ed1>`__)

Fixes
*****

- Fixed issues with Soundcloud playback (`989e16b <https://github.com/Cog-Creators/Red-DiscordBot/commit/989e16b20b814971e01a8657dedf4d9b45c23ed1>`__)
- Added partial mitigation for issues with running Red on Python 3.8 (`1c64abe <https://github.com/Cog-Creators/Red-DiscordBot/commit/1c648abea21c28cd3b912d1cb2fee6cf2960e352>`__)


Redbot 3.1.6 (2019-10-18)
=========================

This is a hotfix release updating discord.py for a critical issue related to voice connections.


Redbot 3.1.5 (2019-07-31)
=========================

This is a maintenance release fixing issues with playback of YouTube tracks.


Redbot 3.1.4 (2019-07-16)
=========================

This is a hotfix release fixing issues with broken custom commands and modlog cases.


Redbot 3.1.3 (2019-07-14)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Bakersbakebread`, :ghuser:`DevilXD`, :ghuser:`DiscordLiz`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`lizzyd710`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Tobotimus`, :ghuser:`yamikaitou`

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added new settings for the invite returned by ``[p]invite`` command (:issue:`1847`)
    
    - ``[p]inviteset public`` - Defines if the command should be accessible for users that aren't bot owners.
    - ``[p]inviteset perms`` - Sets permissions for bot's managed role that can get created automatically when bot is invited.

    For more information, see help of each of the listed commands.
- **Audio** - Added a ``[p]eq`` command group that allows to manage the Audio equalizer (:issue:`2787`, :issue:`2813`)
- **Audio** - Added a ``[p]summon`` command that summons the bot to the voice channel (:issue:`2786`)

Enhancements
************

- **Core Bot** - A server can now have multiple admin and mod roles (:issue:`2783`)
- **Core Bot** - Improved overall performance on Linux and Mac systems by swapping asyncio loop implementation to uvloop (:issue:`2819`)
- **Audio** - Added support for armv6l, aarch32, and aarch64 architectures (:issue:`2755`)
- **Audio** - Improved error handling and added retrying to jar download and Lavalink connection (:issue:`2764`)
- **Audio** - Internal Lavalink manager now accepts any jar with a build number greater than or equal to our release build (:issue:`2656`, :issue:`2785`)
- **Audio** - Increased Lavalink connection timeout to 50 seconds to ensure Lavalink manages to start before the time runs out on lower-end devices (:issue:`2784`)
- **Filter** - Updated name filtering to be consistent with message content filtering (:issue:`2740`, :issue:`2794`)
- **Mod** - ``[p]userinfo`` command now mentions the roles the user has (:issue:`2759`)
- **Modlog** - Improved efficiency of case storage (:issue:`2766`)

Fixes
*****

- **Core Bot** - ``[p]command disable`` and its subcommands now ensure that the command to disable is not ``[p]command`` or any of its subcommands to prevent lockout (:issue:`2770`)
- **Core Bot** - Fixed broken fuzzy help (:issue:`2768`)
- **Core Bot** - Fixed an issue with error message being sent multiple times when help command was unable to DM the user (:issue:`2790`)
- **Core Bot** - Fixed broken link in help of ``[p]set color`` (:issue:`2715`, :issue:`2803`)
- **Core Bot** - Fixed user output and exception handling on cog load/reload (:issue:`2767`)
- **Core Bot** - Fixed substitution of ``[p]`` in command descriptions in non-embedded help output (:issue:`2846`)
- **Core Bot** - Fixed a race condition that could allow a user to run commands they are denied to run by Permissions cog for a short moment before the cog is loaded (:issue:`2857`)
- **Audio** - Added missing bot permission checks to commands in Audio cog (:issue:`2756`)
- **Audio** - Fixed an issue with jar downloading on mixed-filesystem environments (:issue:`2682`, :issue:`2765`)
- **Audio** - Fixed an issue with ``[p]playlist copy`` and ``[p]playlist queue`` failing when the prefix contains certain characters (:issue:`2788`, :issue:`2789`)
- **Audio** - Fixed an issue that caused ``[p]shuffle`` and ``[p]repeat`` to send an error message when the user is not in the voice channel (:issue:`2811`, :issue:`2812`, :issue:`2842`)
- **Filter** - Fixed caching issue that caused filter to use an old list of words to filter (:issue:`2810`)
- **Permissions** - Commands for adding/removing rules in ``[p]permissions`` command group now no longer ignore invalid arguments (:issue:`2851`, :issue:`2865`)
- **Trivia Lists** - Fixed answers for Beethoven-related questions in ``entertainment`` trivia list (:issue:`2318`, :issue:`2823`)


Developer changelog
-------------------

New Functionality
*****************

- Added (optional) ``default_unit`` keyword argument to `TimedeltaConverter` (:issue:`2753`)
- Added `redbot.core.bank.cost()` (:issue:`2761`)
- Added ``UserFeedbackCheckFailure`` (:issue:`2761`)
- Added `Context.react_quietly()` (:issue:`2834`)

Fixes
*****

- Fixed cache issues with Config when the developer accidentally tries to set an object that isn't JSON serializable (:issue:`2793`, :issue:`2796`)
- Fixed an issue with identifiers that contain ``$`` or ``.`` which has caused a KeyError exception regardless of whether such key existed in the data (:issue:`2832`)


Documentation changes
---------------------

Enhancements
************

- Added a warning about the PATH changes to Windows install guide (:issue:`2791`)

Fixes
*****

- Fixed code examples in Bank, Config, and ModLog API documentation (:issue:`2775`, :issue:`2780`, :issue:`2860`)
- Fixed the code example for the documentation of `Command.error` decorator and added a note with clarifications (:issue:`2760`)


Redbot 3.1.2 (2019-05-31)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`bren0xa`, :ghuser:`DevilXD`, :ghuser:`DiscordLiz`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Stonedestroyer`, :ghuser:`Tobotimus`, :ghuser:`yamikaitou`, :ghuser:`zephyrkul`

End-user changelog
------------------

New Functionality
*****************

- **Core Bot** - Added a few new settings for bot's help (:issue:`2667`, :issue:`2681`, :issue:`2676`)

    - ``[p]helpset usemenus`` - Allows the help command to be sent as a paginated menu.
    - ``[p]helpset showhidden`` - Allows the help command to show hidden commands.
    - ``[p]helpset verifychecks``  - Sets if commands which can't be run in the current context should be filtered from help.
    - ``[p]helpset verifyexists`` - Allows the bot to respond indicating the existence of a specific help topic even if the user can't use it.

    For more information, see help of each of the listed commands.
- **Core Bot** - Added ``[p]debuginfo`` command (:issue:`2728`)
- **Core Bot** - Added a generic system that can be used by cog creators to send notifications meant for bot owners (:issue:`2665`, :issue:`2738`, :issue:`2745`)

    This comes with some commands that allow to manage the destinations for the owner notifications.
    See the help of commands in ``[p]set ownernotifications`` command group for more information.
- **Mod** - Added ``[p]slowmode`` command (:issue:`2734`)

Enhancements
************

- **Core Bot** - ``[p]load``, ``[p]unload``, and ``[p]reload`` commands now strip commas from the passed cogs to aid with copy-pasting (:issue:`2693`)
- **Core Bot** - Improved naming consistency of subcommands that *delete* something (:issue:`2731`)
- **Core Bot** - ``[p]set api`` command now allows the user to separate their keys and values with space in addition to commas and semicolons (:issue:`2692`)
- **Downloader** - ``[p]pipinstall`` now indicates that it's doing something (:issue:`2700`)
- **Mod** - ``[p]names`` command no longer requires quoting usernames that contain spaces (:issue:`2675`)
- **Mod** - ``[p]userinfo`` command now mentions the voice channel the user is in (:issue:`2680`)

Fixes
*****

- **Core Bot** - Fixed update notification for bots that have co-owners (:issue:`2677`)
- **Core Bot** - Fixed an issue where bad user input didn't result in the bot sending help for the command (:issue:`2707`)
- **Core Bot** - Fixed an issue with incorrect subcommand descriptions being shown in non-embed help (:issue:`2678`)
- **Core Bot** - Fixed few more issues with help command (:issue:`2676`)
- **Core Bot** - Fixed ``redbot-setup delete`` command failing to delete data path (:issue:`2709`)
- **Core Bot** - Fixed help for commands with no docstring (:issue:`2415`, :issue:`2722`)
- **Core Bot** - Fixed error handling in ``[p]load`` command (:issue:`2686`, :issue:`2688`)
- **Core Bot** - Help menu no longer blocks settings preview in command groups like ``[p]set`` (:issue:`2712`, :issue:`2725`)
- **Core Bot** - Fixed an issue with long cog descriptions in help command (:issue:`2730`)
- **Downloader** - Fixed problems with installing a cog again after uninstalling (:issue:`2685`, :issue:`2690`)
- **General** - Fixed ``[p]urban`` command failure for very long phrase definitions (:issue:`2683`, :issue:`2684`)
- **General** - Fixed issues with ``[p]gif`` and ``[p]gifr`` commands. The bot owner now needs to provide an API key in order to use these commands (:issue:`2653`)
- **Streams** - Fixed an issue with stream commands not properly dealing with stream reruns (:issue:`2679`)
- **Streams** - Fixed a regression that caused stream alerts for non-Twitch users to not work anymore (:issue:`2724`, :issue:`2699`)


Developer changelog
-------------------

New Functionality
*****************

- Added `DictConverter` (:issue:`2692`)
- Added `Red.send_to_owners()` and `Red.get_owner_notification_destinations()` (:issue:`2665`, :issue:`2738`)
- Added `TimedeltaConverter` and `parse_timedelta()` (:issue:`2736`)
- Added ``assume_yes`` attribute to `redbot.core.commands.Context` (:issue:`2746`)

Enhancements
************

- `menu()` now accepts `functools.partial` (:issue:`2718`, :issue:`2720`)


Redbot 3.1.1 (2019-05-15)
=========================

This is a hotfix release fixing issues related to fuzzy command search that were happening with the new help formatter.


Redbot 3.1.0 (2019-05-15)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`calebj`, :ghuser:`DiscordLiz`, :ghuser:`EgonSpengler`, :ghuser:`entchen66`, :ghuser:`FixedThink`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`lionirdeadman`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`NIXC`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Seputaes`, :ghuser:`Sitryk`, :ghuser:`tekulvw`, :ghuser:`Tobotimus`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`zephyrkul`

End-user changelog
------------------

- **Core Bot** - Error messages about cooldowns will now show more friendly representation of cooldown's expiration time (:issue:`2412`)
- **Core Bot** - Cooldown messages are now auto-deleted after cooldown expiration expired (:issue:`2469`)
- **Core Bot** - Fixed local blacklist/whitelist management commands (:issue:`2531`)
- **Core Bot** - ``[p]set locale`` now only accepts actual locales (:issue:`2553`)
- **Core Bot** - ``[p]listlocales`` now includes ``en-US`` locale (:issue:`2553`)
- **Core Bot** - ``redbot --version`` will now give you current version of Red (:issue:`2567`)
- **Core Bot** - Redesigned help and its formatter (:issue:`2628`)
- **Core Bot** - Changed default locale from ``en`` to ``en-US`` (:issue:`2642`)
- **Core Bot** - Added new ``[p]datapath`` command that prints the bot's data path (:issue:`2652`)
- **Core Bot** - Added ``redbot-setup convert`` command which can be used to convert between data backends (:issue:`2579`)
- **Core Bot** - Updated Mongo driver to support large guilds (:issue:`2536`)
- **Core Bot** - Fixed the list of available extras in the ``redbot-launcher`` (:issue:`2588`)
- **Core Bot** - Backup support for Mongo is currently broken (:issue:`2579`)

- **Audio** - Add Spotify support (:issue:`2328`)
- **Audio** - Play local folders via text command (:issue:`2457`)
- **Audio** - Change pause to a toggle (:issue:`2461`)
- **Audio** - Remove aliases (:issue:`2462`)
- **Audio** - Add track length restriction (:issue:`2465`)
- **Audio** - Seek command can now seek to position (:issue:`2470`)
- **Audio** - Add option for dc at queue end (:issue:`2472`)
- **Audio** - Emptydisconnect and status refactor (:issue:`2473`)
- **Audio** - Queue clean and queue clear addition (:issue:`2476`)
- **Audio** - Fix for audioset status (:issue:`2481`)
- **Audio** - Playlist download addition (:issue:`2482`)
- **Audio** - Add songs when search-queuing (:issue:`2513`)
- **Audio** - Match v2 behavior for channel change (:issue:`2521`)
- **Audio** - Bot will no longer complain about permissions when trying to connect to user-limited channel, if it has "Move Members" permission (:issue:`2525`)
- **Audio** - Fix issue on audiostats command when more than 20 servers to display (:issue:`2533`)
- **Audio** - Fix for prev command display (:issue:`2556`)
- **Audio** - Fix for localtrack playing (:issue:`2557`)
- **Audio** - Fix for playlist queue when not playing (:issue:`2586`)
- **Audio** - Track search and append fixes (:issue:`2591`)
- **Audio** - DJ role should ask for a role (:issue:`2606`)
- **DataConverter** - It's dead jim (Removal) (:issue:`2554`)
- **Downloader** - Fixed bug, that caused Downloader to include submodules on cog list (:issue:`2590`)
- **Downloader** - The error message sent by ``[p]cog install`` when required libraries fail to install is now properly formatted (:issue:`2576`)
- **Downloader** - The ``[p]cog uninstall`` command will now remove cog from installed cogs list even if it can't find the cog in install path anymore (:issue:`2595`)
- **Downloader** - The ``[p]cog install`` command will not allow to install cogs which aren't suitable for installed version of Red anymore (:issue:`2605`)
- **Downloader** - The ``[p]cog install`` command will now tell the user that cog has to be loaded after the install (:issue:`2523`)
- **Downloader** - The ``[p]cog uninstall`` command allows to uninstall multiple cogs now (:issue:`2592`)
- **Filter** - Significantly improved performance of Filter cog on large servers (:issue:`2509`)
- **Mod** - Fixed ``[p]ban`` not allowing to omit ``days`` argument (:issue:`2602`)
- **Mod** - Added the command ``[p]voicekick`` to kick members from a voice channel with optional modlog case (:issue:`2639`)
- **Mod** - Admins can now decide how many times message has to be repeated before cog's ``deleterepeats`` functionality removes it (:issue:`2437`)
- **Permissions** - Removed ``[p]p`` alias for ``[p]permissions`` command (:issue:`2467`)
- **Streams** - Added support for setting custom stream alert messages per guild (:issue:`2600`)
- **Streams** - Added ability to exclude Twitch stream reruns (:issue:`2620`)
- **Streams** - Twitch stream reruns are now marked as reruns in embed title (:issue:`2620`)
- **Trivia Lists** - Fixed dead image link for Sao Tome and Principe flag in ``worldflags`` trivia (:issue:`2540`)


Developer changelog
-------------------

Breaking Changes
****************

- **Config** - We now record custom group primary key lengths in the core config object (:issue:`2550`)
- **Downloader** - Cog Developers now have to use ``min_bot_version`` key instead of ``bot_version`` to specify minimum version of Red supported by the cog in ``info.json``, see more information in :ref:`info-json-format` (:issue:`2605`)

New Functionality
*****************

- Added a ``on_message_without_command`` event that is dispatched when bot gets an event for a message that doesn't contain a command (:issue:`2338`)
- **Config** - Introduced `Config.init_custom()` method (:issue:`2545`)
- **Downloader** - Added ``max_bot_version`` key to ``info.json`` that allows to specify maximum supported version of Red supported by the cog in ``info.json``, see more information in :ref:`info-json-format`. (:issue:`2605`)
- **Utility Functions** - Added `chat_formatting.humanize_timedelta()` (:issue:`2412`)

Enhancements
************

- Red is now no longer vendoring discord.py and installs it from PyPI (:issue:`2587`)
- Upgraded discord.py dependency to version 1.0.1 (:issue:`2587`)
- Usage of ``yaml.load`` will now warn about its security issues (:issue:`2326`)
- **Config** - Migrated internal UUIDs to maintain cross platform consistency (:issue:`2604`)
- **Utility Functions** - Improved error handling of empty lists in `chat_formatting.humanize_list()` (:issue:`2597`)

Fixes
*****

- **Utility Functions** - Fixed spelling of the `Tunnel`'s method from ``files_from_attatch()`` to `files_from_attach() <Tunnel.files_from_attach()>`; old name was left for backwards compatibility (:issue:`2496`)
- **Utility Functions** - Fixed behavior of ``Tunnel.react_close()`` - now when tunnel closes, the message will be sent to the other end (:issue:`2507`)


Redbot 3.0.2 (2019-02-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Tobotimus`, :ghuser:`ZeLarpMaster`

End-user changelog
------------------

Fixes
*****

- **Permissions** - Fixed rules loading for cogs (`431cdf1 <https://github.com/Cog-Creators/Red-DiscordBot/commit/431cdf1ad4247fbe40f940e39bac4c919b470937>`__)
- **Trivia Lists** - Fixed a typo in ``cars`` trivia (:issue:`2475`)


Redbot 3.0.1 (2019-02-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`calebj`, :ghuser:`DiscordLiz`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Redjumpman`, :ghuser:`Tobotimus`, :ghuser:`Twentysix26`, :ghuser:`ZeLarpMaster`, :ghuser:`zephyrkul`

End-user changelog
------------------

Enhancements
************

- **Core Bot** - Improve some of the core commands to not require double quotes for arguments with spaces, if they're the last argument required by the command (:issue:`2407`)
- **Core Bot** - Using ``[p]load`` command now sends help message when it's used without arguments (:issue:`2432`)
- **Downloader** - The ``[p]pipinstall`` command now sends help message when it's used without arguments (`eebed27 <https://github.com/Cog-Creators/Red-DiscordBot/commit/eebed27fe76aa5b51cfa38ac9a35bd182d881352>`__)
- **Mod** - Usernames and nicknames listed in ``[p]names`` and ``[p]userinfo`` commands now have the spoiler markdown escaped (:issue:`2401`)
- **Modlog** - Usernames listed in modlog cases now have the spoiler markdown escaped (:issue:`2401`)
- **Warnings** - Members can now also be passed with username, nickname, or user mention to ``[p]warnings`` and ``[p]unwarn`` commands (:issue:`2403`, :issue:`2404`)

Fixes
*****

- **Core Bot** - Messages sent interactively (i.e. prompting user whether they would like to view the next message) now no longer cause errors if bot's prompt message gets removed by other means (:issue:`2380`, :issue:`2447`)
- **Core Bot** - Fixed error in ``[p]servers`` command that was happening when bot's prompt message was deleted before the prompt time was over (:issue:`2400`)
- **Core Bot** - Fixed behavior of CLI arguments in ``redbot-launcher`` (:issue:`2432`)
- **Audio** - Fixed issues with setting external Lavalink (:issue:`2306`, :issue:`2460`)
- **Audio** - Audio now cleans up zombie players from guilds it's no longer in (:issue:`2414`)
- **Downloader** - Fixed issues with cloning that happened if instance's data path had spaces (:issue:`2421`)
- **Mod** - ``[p]userinfo`` now accounts for guild's lurkers (:issue:`2406`, :issue:`2426`)
- **Permissions** - Fixed rule precedence issues for default rules (:issue:`2313`, :issue:`2422`)


Developer changelog
-------------------

New Functionality
*****************

- **Utility Functions** - Added `escape_spoilers()` and `escape_spoilers_and_mass_mentions()` methods for escaping strings with spoiler markdown (:issue:`2401`)

Fixes
*****

- **Utility Functions** - ``MessagePredicate.lower_contained_in()`` now actually lowers the message content before trying to match (:issue:`2399`)


Redbot 3.0.0 (2019-01-28)
=========================

First stable release of Red V3.
Changelogs for this and previous versions can be found on `our GitHub releases page <https://github.com/Cog-Creators/Red-DiscordBot/releases?after=3.0.1>`__.
