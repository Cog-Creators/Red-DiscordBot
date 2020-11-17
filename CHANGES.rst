.. Red changelogs

3.4.14 (2021-09-23)
===================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`L33Tech`, :ghuser:`maxbooiii`, :ghuser:`RheingoldRiver`

Read before updating
--------------------

#. Versions of RHEL older than 8.4 (including 7) and versions of CentOS older than 8.4 (excluding 7) are no longer supported.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.14 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1239>`__.


End-user changelog
------------------

- **Core Bot** - Added the new native Discord timestamp in the ``[p]uptime`` command (:issue:`5323`)
- **Core Bot** - ``redbot-setup delete`` command no longer requires database connection if the data deletion was not requested (:issue:`5312`, :issue:`5313`)
- **Audio** - Fixed intermittent 403 Forbidden errors (:issue:`5329`)
- **Modlog** - Fixed formatting of **Last modified at** field in Modlog cases (:issue:`5317`)


Documentation changes
---------------------

- Each operating system now has a dedicated install guide (:issue:`5328`)
- Fixed Raspberry Pi OS install guide (:issue:`5314`, :issue:`5328`)
- Added install guide for CentOS Stream 8, Oracle Linux 8.4-8.x, and Rocky Linux 8 (:issue:`5328`)
- Install guides for RHEL derivatives no longer require the use of pyenv (:issue:`5328`)


3.4.13 (2021-09-09)
===================

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

Core Bot
********

- Added a new ``[p]diagnoseissues`` command to allow the bot owners to diagnose issues with various command checks with ease (:issue:`4717`, :issue:`5243`)

    Since some of us are pretty excited about this feature, here's a very small teaser showing a part of what it can do:

    .. figure:: https://user-images.githubusercontent.com/6032823/132610057-d6c65d67-c244-4f0b-9458-adfbe0c68cab.png

- Revamped the ``[p]debuginfo`` to make it more useful for... You guessed it, debugging! (:issue:`4997`, :issue:`5156`)

    More specifically, added information about CPU and RAM, bot's instance name and owners

- The formatting of Red's console logs has been updated to make it more copy-paste friendly (:issue:`4868`, :issue:`5181`)
- Added the new native Discord timestamps in Modlog cases, ``[p]userinfo``, ``[p]serverinfo``, and ``[p]tempban`` (:issue:`5155`, :issue:`5241`)
- Added a setting for ``[p]help``'s reaction timeout (:issue:`5205`)

    This can be changed with ``[p]helpset reacttimeout`` command

- Red 3.4.13 is the first release to (finally) support Python 3.9! (:issue:`4655`, :issue:`5121`)
- Upgraded all Red's dependencies (:issue:`5121`)
- Fedora 32 is no longer supported as it has already reached end of life (:issue:`5121`)
- Fixed a bunch of errors related to the missing permissions and channels/messages no longer existing (:issue:`5109`, :issue:`5163`, :issue:`5172`, :issue:`5191`)

Admin
*****

- The ``[p]selfroleset add`` and ``[p]selfroleset remove`` commands can now be used to add multiple selfroles at once (:issue:`5237`, :issue:`5238`)

Alias
*****

- Added commands for editing existing aliases (:issue:`5108`)

Audio
*****

- Added a per-guild max volume setting (:issue:`5165`)

    This can be changed with the ``[p]audioset maxvolume`` command

- Fixed an issue with short clips being cutoff when auto-disconnect on queue end is enabled (:issue:`5158`, :issue:`5188`)
- Fixed fetching of age-restricted tracks (:issue:`5233`)
- Fixed searching of YT Music (:issue:`5233`)
- Fixed playback from SoundCloud (:issue:`5233`)
- ``[p]summon`` will now indicate that it has succeeded or failed to summon the bot (:issue:`5186`)

Cleanup
*******

- The ``[p]cleanup user`` command can now be used to clean messages of a user that is no longer in the server (:issue:`5169`)
- All ``[p]cleanup`` commands will now send a notification with the number of deleted messages. The notification is deleted automatically after 5 seconds (:issue:`5218`)

    This can be disabled with the ``[p]cleanupset notify`` command

Downloader
**********

- The dot character (``.``) can now be used in repo names. No more issues with adding repositories using the commands provided by the Cog Index! (:issue:`5214`)

Filter
******

- Added ``[p]filter clear`` and ``[p]filter channel clear`` commands for clearing the server's/channel's filter list (:issue:`4841`, :issue:`4981`)

Mod
***

- Fixed an error with handling of temporary ban expirations while the guild is unavailable due to Discord outage (:issue:`5173`)
- The DM message from the ``[p]tempban`` command will now include the ban reason if ``[p]modset dm`` setting is enabled (:issue:`4836`, :issue:`4837`)
- The ``[p]rename`` command will no longer permit changing nicknames of members that are not lower in the role hierarchy than the command caller (:issue:`5187`, :issue:`5211`)

Streams
*******

- Fixed an issue with some YouTube streamers getting removed from stream alerts after a while (:issue:`5195`, :issue:`5223`)
- Made small optimizations in regards to stream alerts (:issue:`4968`)

Trivia
******

- Added schema validation of the custom trivia files (:issue:`4571`, :issue:`4659`)

Warnings
********

- 0 point warnings are, once again, allowed. (:issue:`5177`, :issue:`5178`)


Developer changelog
-------------------

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

- Added a document about (privileged) intents and our stance regarding "public bots" (:issue:`5216`, :issue:`5221`)
- Added install instructions for Debian 11 Bullseye (:issue:`5213`, :issue:`5217`)
- Added Oracle Cloud's Always Free offering to the :ref:`host-list` (:issue:`5225`)
- Updated the commands in the install guide for Mac OS to work properly on Apple Silicon devices (:issue:`5234`)
- Fixed the examples of commands that are only available to people with the mod role (:issue:`5180`)
- Fixed few other small issues with the documentation :) (:issue:`5048`, :issue:`5092`, :issue:`5149`, :issue:`5207`, :issue:`5209`, :issue:`5215`, :issue:`5219`, :issue:`5220`)


Miscellaneous
-------------

- **Core Bot** - The console error about missing Privileged Intents stands out more now (:issue:`5184`)
- **Core Bot** - The ``[p]invite`` command will now add a tick reaction after it DMs an invite link to the user (:issue:`5184`)
- **Downloader** - Added a few missing line breaks (:issue:`5185`, :issue:`5187`)


3.4.12 (2021-06-17)
===================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`npc203`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Stonedestroyer`

This is a hotfix release related to Red ceasing to use the Audio Global API service.

Full changelog
--------------

- **Audio** - Updated URL of the curated playlist (:issue:`5135`)
- **Audio** - All local caches are now enabled by default (:issue:`5140`)
- **Audio** - Global API service will no longer be used in Audio and as such support for it has been removed from the cog (:issue:`5143`)
- **Core Bot** - ``[p]set serverprefix`` command will now prevent the user from setting a prefix with length greater than 20 characters (:issue:`5091`, :issue:`5117`)
- **Core Bot** - ``[p]set prefix`` command will now warn the user when trying to set a prefix with length greater than 20 characters (:issue:`5091`, :issue:`5117`)
- **Core Bot** - ``applications.commands`` scope can now be included in the invite URL returned from ``[p]invite`` by enabling it with``[p]inviteset commandscope``
- **Dev Cog** - ``[p]debug`` command will now confirm the code finished running with a tick reaction (:issue:`5107`)
- **Filter** - Fixed an edge case that caused the cog to sometimes check contents of DM messages (:issue:`5125`)
- **Warnings** - Prevented users from applying 0 or less points in custom warning reasons (:issue:`5119`, :issue:`5120`)


3.4.11 (2021-06-12)
===================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Onii-Chan-Discord`

This is a hotfix release fixing a crash involving guild uploaded stickers.

Full changelog
--------------

- discord.py version has been bumped to 1.7.3 (:issue:`5129`)
- Links to the CogBoard in Red's documentation have been updated to use the new domain (:issue:`5124`)


3.4.10 (2021-05-28)
===================

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

Core Bot
********

- Fixed terminal colors on Windows (:issue:`5063`)
- Fixed the ``--rich-traceback-extra-lines`` flag (:issue:`5028`)
- Added missing information about the ``showaliases`` setting in ``[p]helpset showsettings`` (:issue:`4971`)
- The help command no longer errors when it doesn't have permission to read message history and menus are enabled (:issue:`4959`, :issue:`5030`)
- Fixed a bug in ``[p]embedset user`` that made it impossible to reset the user's embed setting (:issue:`4962`)
- ``[p]embedset command`` and its subcommands now properly check whether any of the passed command's parents require Embed Links permission (:issue:`4962`)
- Fixed an issue with Red reloading unrelated modules when using ``[p]load`` and ``[p]reload`` (:issue:`4956`, :issue:`4958`)

Admin
*****

- The cog will now log when it leaves a guild due to the serverlock (:issue:`5008`, :issue:`5073`)

Audio
*****

- Fixed an issue that made it possible to remove Aikaterna's curated tracks playlist (:issue:`5018`)
- Fixed auto-resume of auto play after Lavalink restart (:issue:`5051`)
- The ``[p]audiostats`` command can now only be used by bot owners (:issue:`5017`)
- Fixed an error with ``[p]audiostats`` caused by players not always having their connection time stored (:issue:`5046`)
- Fixed track resuming in a certain edge case (:issue:`4996`)
- Fixed an error in ``[p]audioset restart`` (:issue:`4987`)
- The cog will now check whether it has speak permissions in the channel before performing any actions (:issue:`5012`)
- Fixed an issue with Audio failing when it's missing permissions to send a message in the notification channel (:issue:`4960`)
- Fixed fetching of age-restricted tracks (:issue:`5085`)
- Fixed an issue with Soundcloud URLs that ended with a slash (``/``) character (:issue:`5085`)

Custom Commands
***************

- ``[p]customcom create simple`` no longer errors for a few specific names (:issue:`5026`, :issue:`5027`)

Downloader
**********

- ``[p]repo remove`` can now remove multiple repos at the same time (:issue:`4765`, :issue:`5082`)
- ``[p]cog install`` now properly shows the repo name rather than ``{repo.name}`` (:issue:`4954`)

Mod
***

- ``[p]mute`` no longer errors on muting a bot user if the ``senddm`` option is enabled (:issue:`5071`)

Mutes
*****

- Forbidden errors during the channel mute are now handled properly in a rare edge case (:issue:`4994`)

Modlog
******

- ``[p]modlogset resetcases`` will now ask for confirmation before proceeding (:issue:`4976`)
- Modlog will no longer try editing the case's Discord message once it knows that it no longer exists (:issue:`4975`)

Streams
*******

- Fixed Picarto support (:issue:`4969`, :issue:`4970`)
- ``[p]twitchstream``, ``[p]youtubestream``, and ``[p]picarto`` commands can no longer be run in DMs (:issue:`5036`, :issue:`5035`)
- Smashcast service has been closed and for that reason we have removed support for it from the cog (:issue:`5039`, :issue:`5040`)
- Fixed Twitch stream alerts for streams that use localized display names (:issue:`5050`, :issue:`5066`)
- The cog no longer errors when trying to delete a cached message from a channel that no longer exists (:issue:`5032`, :issue:`5031`)
- In message template, ``{stream.display_name}`` can now be used to refer to streamer's display name (:issue:`5050`, :issue:`5066`)

    - This is not always the same as ``{stream}`` which refers to the streamer's channel or username

Warnings
********

- The warn action is now taken *after* sending the warn message to the member (:issue:`4713`, :issue:`5004`)


Developer changelog
-------------------

- Bumped discord.py to 1.7.2 (:issue:`5066`)
- The log messages shown by the global error handler will now show the trace properly for task done callbacks (:issue:`4980`)
- **Dev** - ``[p]eval``, ``[p]repl``, and ``[p]debug`` commands no longer fail to send very long syntax errors (:issue:`5041`)
- **Dev** - ``[p]eval``, ``[p]repl``, and ``[p]debug`` commands now, in addition to ``py``, support code blocks with ``python`` syntax (:issue:`5083`)


Documentation changes
---------------------

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
- Removed PM2 guide (:issue:`4991`)


Miscellaneous
-------------

- Clarified that ``[p]cleanup`` commands only delete the messages from the current channel (:issue:`5070`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5025`)
- Added information on how to set the bot not to start on boot anymore to auto-restart docs (:issue:`5020`)
- Improved logging in Audio cog (:issue:`5044`)
- Improved logging of API errors in Streams cog (:issue:`4995`)
- The command ``[p]urban`` from the General cog will now use the default embed color of the bot (:issue:`5014`)
- Cog creation guide now includes the ``bot`` as an argument to the cog class (:issue:`4988`)
- Rephrased a few strings and fixed maaaaany grammar issues and typos (:issue:`4793`, :issue:`4832`, :issue:`4955`, :issue:`4966`, :issue:`5015`, :issue:`5019`, :issue:`5029`, :issue:`5038`, :issue:`5055`, :issue:`5080`, :issue:`5081`)


3.4.9 (2021-04-06)
==================

This is a hotfix release fixing an issue with command error handling.

discord.py version has been bumped to 1.7.1.

Thanks again to :ghuser:`Rapptz` for quick response on this issue.


3.4.8 (2021-04-06)
==================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`6days9weeks`, :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kingslayer268`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Obi-Wan3`, :ghuser:`OofChair`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`rijusougata13`, :ghuser:`TheDiscordHistorian`, :ghuser:`Tobotimus`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.8 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1212>`__.

#. Fedora 31 and OpenSUSE Leap 15.1 are no longer supported as they have already reached end of life.


End-user changelog
------------------

Core Bot
********

- Added per-command embed settings (:issue:`4049`)

    - See help of ``[p]embedset`` and ``[p]embedset command`` command group for more information

- The ``[p]servers`` command uses menus now (:issue:`4720`, :issue:`4831`)
- ``[p]leave`` accepts server IDs now (:issue:`4831`)
- Commands for listing global and local allowlists and blocklists will now, in addition to IDs, contain user/role names (:issue:`4839`)
- Messages sent interactively in DM channels no longer fail (:issue:`4876`)
- An error message will now be shown when a command that is only available in NSFW channels is used in a non-NSFW channel (:issue:`4933`)
- Added more singular and plural forms in a bunch of commands in the bot (:issue:`4004`, :issue:`4898`)
- Removed the option to drop the entire PostgreSQL database in ``redbot-setup delete`` due to limitations of PostgreSQL (:issue:`3699`, :issue:`3833`)
- Added a progress bar to ``redbot-setup convert`` (:issue:`2952`)
- Fixed how the command signature is shown in help for subcommands that have group args (:issue:`4928`)

Alias
*****

- Fixed issues with command aliases for commands that take an arbitrary, but non-zero, number of arguments (e.g. ``[p]load``) (:issue:`4766`, :issue:`4871`)

Audio
*****

- Fixed stuttering (:issue:`4565`)
- Fixed random disconnects (:issue:`4565`)
- Fixed the issues causing the player to be stuck on 00:00 (:issue:`4565`)
- Fixed ghost players (:issue:`4565`)
- Audio will no longer stop playing after a while (:issue:`4565`)
- Fixed playlist loading for playlists with over 100 songs (:issue:`4932`)
- Fixed an issue with alerts causing errors in playlists being loaded (:issue:`4932`)
- Improved playlist extraction (:issue:`4932`)
- Fixed an issue with consent pages appearing while trying to load songs or playlists (:issue:`4932`)

Cleanup
*******

- ``[p]cleanup before`` and ``[p]cleanup after`` commands can now be used without a message ID if the invocation message replies to some message (:issue:`4790`)

Downloader
**********

- Improved compatibility with Git 2.31 and newer (:issue:`4897`)

Filter
******

- Added meaningful error messages for incorrect arguments in the ``[p]bank set`` command (:issue:`4789`, :issue:`4801`)

Mod
***

- Improved performance of checking tempban expirations (:issue:`4907`)
- Fixed tracking of nicknames that were set just before nick reset (:issue:`4830`)

Mutes
*****

- Vastly improved performance of automatic unmute handling (:issue:`4906`)

Streams
*******

- Streams cog should now load faster on bots that have many stream alerts set up (:issue:`4731`, :issue:`4742`)
- Fixed possible memory leak related to automatic message deletion (:issue:`4731`, :issue:`4742`)
- Streamer accounts that no longer exist are now properly handled (:issue:`4735`, :issue:`4746`)
- Fixed stream alerts being sent even after unloading Streams cog (:issue:`4940`)
- Checking Twitch streams will now make less API calls (:issue:`4938`)
- Ratelimits from Twitch API are now properly handled (:issue:`4808`, :issue:`4883`)

Trivia
******

- Added a new option for hiding the answer to the Trivia answer in a spoiler (:issue:`4700`, :issue:`4877`)

    - ``[p]triviaset usespoilers`` command can be used to enable/disable this option

Warnings
********

- Fixed output of ``[p]warnings`` command for members that are no longer in the server (:issue:`4900`, :issue:`4904`)
- Embeds now use the default embed color of the bot (:issue:`4878`)


Developer changelog
-------------------

- Bumped discord.py version to 1.7.0 (:issue:`4928`)
- Deprecated importing ``GuildConverter`` from ``redbot.core.commands.converter`` namespace (:issue:`4928`)

    - ``discord.Guild`` or ``GuildConverter`` from ``redbot.core.commands`` should be used instead
- Added ``guild`` parameter to `bot.allowed_by_whitelist_blacklist() <Red.allowed_by_whitelist_blacklist()>` which is meant to replace the deprecated ``guild_id`` parameter (:issue:`4905`, :issue:`4914`)

    - Read the method's documentation for more information
- Fixed ``on_red_api_tokens_update`` not being dispatched when the tokens were removed with ``[p]set api remove`` (:issue:`4916`, :issue:`4917`)


Documentation changes
---------------------

- Added a note about updating cogs in update message and documentation (:issue:`4910`)
- Added `cog guide for Image cog <cog_guides/image>` (:issue:`4821`)
- Updated Mac install guide with new ``brew`` commands (:issue:`4865`)
- `getting-started` now contains an explanation of parameters that can take an arbitrary number of arguments (:issue:`4888`, :issue:`4889`)
- Added a warning to Arch Linux install guide about the instructions being out-of-date (:issue:`4866`)
- All shell commands in the documentation are now prefixed with an unselectable prompt (:issue:`4908`)
- `systemd-service-guide` now asks the user to create the new service file using ``nano`` text editor (:issue:`4869`, :issue:`4870`)

    - Instructions for all Linux-based operating systems now recommend to install ``nano``
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`4864`, :issue:`4942`)


3.4.7 (2021-02-26)
==================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`elijabesu`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`palmtree5`, :ghuser:`TrustyJAID`

End-user changelog
------------------

- Added proper permission checks to ``[p]muteset senddm`` and ``[p]muteset showmoderator`` (:issue:`4849`)
- Updated the ``[p]lmgtfy`` command to use the new domain (:issue:`4840`)
- Updated the ``[p]info`` command to more clearly indicate that the instance is owned by a team (:issue:`4851`)
- Fixed minor issues with error messages in Mutes cog (:issue:`4847`, :issue:`4850`, :issue:`4853`)

Documentation changes
---------------------

- Added `cog guide for General cog <cog_guides/general>` (:issue:`4797`)
- Added `cog guide for Trivia cog <cog_guides/trivia>` (:issue:`4566`)


3.4.6 (2021-02-16)
==================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`Andeeeee`, :ghuser:`bobloy`, :ghuser:`BreezeQS`, :ghuser:`Danstr5544`, :ghuser:`Dav-Git`, :ghuser:`Elysweyr`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`NeuroAssassin`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Strafee`, :ghuser:`TheWyn`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.6 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1199>`__.


End-user changelog
------------------

Core Bot
********

- Fixed the rotation of Red's logs that could before result in big disk usage (:issue:`4405`, :issue:`4738`)
- Fixed command usage in the help messages for few commands in Red (:issue:`4599`, :issue:`4733`)
- Fixed errors in ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands (:issue:`4767`, :issue:`4768`)
- ``[p]command listdisabled guild`` can no longer be run in DMs (:issue:`4771`, :issue:`4772`)
- Improvements and fixes for our new (colorful) logging (:issue:`4702`, :issue:`4726`)

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

- Added a friendly error message to ``[p]load`` that is shown when trying to load a cog with a command name that is already taken by a different cog (:issue:`3870`)
- Help now includes command aliases in the command help (:issue:`3040`)

    - This can be disabled with ``[p]helpset showaliases`` command

- Fixed errors appearing when using Ctrl+C to interrupt ``redbot --edit`` (:issue:`3777`, :issue:`4572`)

Admin
*****

- ``[p]selfrole`` can now be used without a subcommand and passed with a selfrole directly to add/remove it from the user running the command (:issue:`4826`)

Audio
*****

- Improved detection of embed players for fallback on age-restricted YT tracks (:issue:`4818`, :issue:`4819`)
- Improved MP4/AAC decoding (:issue:`4818`, :issue:`4819`)
- Requests for YT tracks are now retried if the initial request causes a connection reset (:issue:`4818`, :issue:`4819`)

Cleanup
*******

- Renamed the ``[p]cleanup spam`` command to ``[p]cleanup duplicates``, with the old name kept as an alias for the time being (:issue:`4814`)
- Fixed an error from passing an overly large integer as a message ID to ``[p]cleanup after`` and ``[p]cleanup before`` (:issue:`4791`)

Dev Cog
*******

- Help descriptions of the cog and its commands now get translated properly (:issue:`4815`)

Economy
*******

- ``[p]economyset rolepaydayamount`` can now remove the previously set payday amount (:issue:`4661`, :issue:`4758`)

Filter
******

- Added a case type ``filterhit`` which is used to log filter hits (:issue:`4676`, :issue:`4739`)

Mod
***

- The ``[p]tempban`` command no longer errors out when trying to ban a user in a guild with the vanity url feature that doesn't have a vanity url set (:issue:`4714`)
- Fixed an edge case in role hierarchy checks (:issue:`4740`)
- Added two new settings for disabling username and nickname tracking (:issue:`4799`)

    - Added a command ``[p]modset trackallnames`` that disables username tracking and overrides the nickname tracking setting for all guilds
    - Added a command ``[p]modset tracknicknames`` that disables nickname tracking in a specific guild

- Added a command ``[p]modset deletenames`` that deletes all stored usernames and nicknames (:issue:`4827`)
- Added usage examples to ``[p]kick``, ``[p]ban``, ``[p]massban``, and ``[p]tempban`` (:issue:`4712`, :issue:`4715`)
- Updated DM on kick/ban to use bot's default embed color (:issue:`4822`)

Modlog
******

- Added a command ``[p]listcases`` that allows you to see multiple cases for a user at once (:issue:`4426`)
- Added typing indicator to ``[p]casesfor`` command (:issue:`4426`)

Mutes
*****

- Fixed an edge case in role hierarchy checks (:issue:`4740`)
- The modlog reason no longer contains leading whitespace when it's passed *after* the mute time (:issue:`4749`)
- A DM can now be sent to the (un)muted user on mute and unmute (:issue:`3752`, :issue:`4563`)

    - Added ``[p]muteset senddm`` to set whether the DM should be sent (function disabled by default)
    - Added ``[p]muteset showmoderator`` to set whether the DM sent to the user should include the name of the moderator that muted the user (function disabled by default)

- Added more role hierarchy checks to ensure permission escalations cannot occur on servers with a careless configuration (:issue:`4741`)
- Help descriptions of the cog and its commands now get translated properly (:issue:`4815`)

Reports
*******

- Reports now use the default embed color of the bot (:issue:`4800`)

Streams
*******

- Fixed incorrect timezone offsets for some YouTube stream schedules (:issue:`4693`, :issue:`4694`)
- Fixed meaningless errors happening when the YouTube API key becomes invalid or when the YouTube quota is exceeded (:issue:`4745`)

Trivia
******

- Payout for trivia sessions ending in a tie now gets split between all the players with the highest score (:issue:`3931`, :issue:`4649`)

Trivia Lists
************

- Added new Who's That Pokémon - Gen. VI trivia list (:issue:`4785`)
- Updated answers regarding some of the hero's health and abilities in the ``overwatch`` trivia list (:issue:`4805`)


Developer changelog
-------------------

Core Bot
********

- Updated versions of the libraries used in Red: discord.py to 1.6.0, aiohttp to 3.7.3 (:issue:`4728`)
- Added an event ``on_red_before_identify`` that is dispatched before IDENTIFYing a session (:issue:`4647`)

Utility Functions
*****************

- Added a function `redbot.core.utils.chat_formatting.spoiler()` that wraps the given text in a spoiler (:issue:`4754`)

Dev Cog
*******

- Cogs can now add their own variables to the environment of ``[p]debug``, ``[p]eval``, and ``[p]repl`` commands (:issue:`4667`)

    - Variables can be added and removed from the environment of Dev cog using two new methods:

        - `bot.add_dev_env_value() <Red.add_dev_env_value()>`
        - `bot.remove_dev_env_value() <Red.remove_dev_env_value()>`


Documentation changes
---------------------

- Added `cog guide for Filter cog <cog_guides/filter>` (:issue:`4579`)
- Added information about the Red Index to `guide_publish_cogs` (:issue:`4778`)
- Restructured the host list (:issue:`4710`)
- Clarified how to use pm2 with ``pyenv virtualenv`` (:issue:`4709`)
- Updated the pip command for Red with the postgres extra in Linux/macOS install guide to work on zsh shell (:issue:`4697`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`4770`)


Miscellaneous
-------------

- Various grammar fixes (:issue:`4705`, :issue:`4748`, :issue:`4750`, :issue:`4763`, :issue:`4788`, :issue:`4792`, :issue:`4810`)
- Red's dependencies have been bumped (:issue:`4572`)


3.4.5 (2020-12-24)
==================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Injabie3`, :ghuser:`NeuroAssassin`

End-user changelog
------------------

Streams
*******

- Fixed Streams failing to load and work properly (:issue:`4687`, :issue:`4688`)


3.4.4 (2020-12-24)
==================

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

Core Bot
********

- Red's logging will now shine in your terminal more than ever (:issue:`4577`)
- Improved consistency of command usage in the help messages within all commands in Core Red (:issue:`4589`)
- Added a friendly error when the duration provided to commands that use the ``commands.TimedeltaConverter`` converter is out of the maximum bounds allowed by Python interpreter (:issue:`4019`, :issue:`4628`, :issue:`4630`)
- Fixed an error when removing path from a different operating system than the bot is currently running on with ``[p]removepath`` (:issue:`2609`, :issue:`4662`, :issue:`4466`)

Audio
*****

- Fixed ``[p]llset java`` failing to set the Java executable path (:issue:`4621`, :issue:`4624`)
- Fixed Soundcloud playback (:issue:`4683`)
- Fixed YouTube age-restricted track playback (:issue:`4683`)
- Added more friendly messages for 429 errors to let users know they have been temporarily banned from accessing the service instead of a generic Lavalink error (:issue:`4683`)
- Environment information will now be appended to Lavalink tracebacks in the spring.log (:issue:`4683`)

Cleanup
*******

- ``[p]cleanup self`` will now delete the command message when the bot has permissions to do so (:issue:`4640`)

Dev
***

- Added new ``[p]bypasscooldown`` command that allows owners to bypass command cooldowns (:issue:`4440`)

Economy
*******

- ``[p]economyset slotmin`` and ``[p]economyset slotmax`` now warn when the new value will cause the slots command to not work (:issue:`4583`)

General
*******

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4678`)

Mod
***

- ``[p]ban`` command will no longer error out when the given reason is too long (:issue:`4187`, :issue:`4189`)

Streams
*******

- Scheduled YouTube streams now work properly with the cog (:issue:`3691`, :issue:`4615`)
- YouTube stream schedules are now announced before the stream (:issue:`4615`)

    - Alerts about YouTube stream schedules can be disabled with a new ``[p]streamset ignoreschedule`` command (:issue:`4615`)

- Improved error logging (:issue:`4680`)

Trivia Lists
************

- Added ``whosthatpokemon5`` trivia list containing Pokémon from the 5th generation (:issue:`4646`)
- Added ``geography`` trivia list (:issue:`4618`)


Developer changelog
-------------------

- `get_audit_reason()` can now be passed a ``shorten`` keyword argument which will automatically shorten the returned audit reason to fit the max length allowed by Discord audit logs (:issue:`4189`)
- ``bot.remove_command()`` now returns the command object of the removed command as does the equivalent method from `discord.ext.commands.Bot` class (:issue:`4636`)


Documentation changes
---------------------

- Added `cog guide for Downloader cog <cog_guides/downloader>` (:issue:`4511`)
- Added `cog guide for Economy cog <cog_guides/economy>` (:issue:`4519`)
- Added `cog guide for Streams cog <cog_guides/streams>` (:issue:`4521`)
- Added `guide_cog_creators` document (:issue:`4637`)
- Removed install instructions for Ubuntu 16.04 (:issue:`4650`)


3.4.3 (2020-11-16)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`KianBral`, :ghuser:`maxbooiii`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.3 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1132>`__.

End-user changelog
------------------

Core Bot
********

- Added ``[p]set competing`` command that allows users to set the bot's competing status (:issue:`4607`, :issue:`4609`)

Audio
*****

- Volume changes on ARM systems running a 64 bit OS will now work again (:issue:`4608`)
- Fixed only 100 results being returned on a Youtube playlist (:issue:`4608`)
- Fixed YouTube VOD duration being set to unknown (:issue:`3885`, :issue:`4608`)
- Fixed some YouTube livestreams getting stuck (:issue:`4608`)
- Fixed internal Lavalink manager failing for Java with untypical version formats (:issue:`4608`)
- Improved AAC audio handling (:issue:`4608`)
- Added support for SoundCloud HLS streams (:issue:`4608`)

Economy
*******

- The ``[p]leaderboard`` command no longer fails in DMs when a global bank is used (:issue:`4569`)

Mod
***

- The ban reason is now properly set in the audit log and modlog when using the ``[p]massban`` command (:issue:`4575`)
- The ``[p]userinfo`` command now shows the new Competing activity (:issue:`4610`, :issue:`4611`)

Modlog
******

- The ``[p]case`` and ``[p]casesfor`` commands no longer fail when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)

Mutes
*****

- Fixed automatic remuting on member join for indefinite mutes (:issue:`4568`)

Trivia
******

- ``[p]triviaset custom upload`` now ensures that the filename is lowercase when uploading (:issue:`4594`)

Developer changelog
-------------------

- ``modlog.get_case()`` and methods using it no longer raise when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)

Documentation changes
---------------------

- Added `guide for Cog Manager UI <cogmanagerui>` (:issue:`4152`)
- Added `cog guide for CustomCommands cog <customcommands>` (:issue:`4490`)


3.4.2 (2020-10-28)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.2 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1128>`__.

End-user changelog
------------------

- **Core Bot** - Added info about the metadata file to ``redbot --debuginfo`` (:issue:`4557`)
- **Audio** - Fixed the ``[p]local search`` command (:issue:`4553`)
- **Audio** - Fixed random "Something broke when playing the track." errors for YouTube tracks (:issue:`4559`)
- **Audio** - Commands in ``[p]llset`` group can now be used in DMs (:issue:`4562`)
- **Mod** - Fixed ``[p]massban`` not working for banning members that are in the server (:issue:`4556`, :issue:`4555`)
- **Streams** - Added error messages when exceeding the YouTube quota in the Streams cog (:issue:`4552`)
- **Streams** - Improved logging for unexpected errors in the Streams cog (:issue:`4552`)

Documentation changes
---------------------

- Added `cog guide for Cleanup cog <cleanup>` (:issue:`4488`)
- Removed multi-line commands from Linux install guides to avoid confusing readers (:issue:`4550`)


3.4.1 (2020-10-27)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`absj30`, :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`chloecormier`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Generaleoley`, :ghuser:`hisztendahl`, :ghuser:`jack1142`, :ghuser:`KaiGucci`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`NeuroAssassin`, :ghuser:`nfitzen`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`PythonTryHard`, :ghuser:`SharkyTheKing`, :ghuser:`Stonedestroyer`, :ghuser:`thisisjvgrace`, :ghuser:`TrustyJAID`, :ghuser:`TurnrDev`, :ghuser:`Vexed01`, :ghuser:`Vuks69`, :ghuser:`xBlynd`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. This release fixes a security issue in Mod cog. See `Security changelog below <important-341-2>` for more information.
#. This Red update bumps discord.py to version 1.5.1, which explicitly requests Discord intents. Red requires all Privileged Intents to be enabled. More information can be found at :ref:`enabling-privileged-intents`.
#. Mutes functionality has been moved from the Mod cog to a new separate cog (Mutes) featuring timed and role-based mutes. If you were using it (or want to start now), you can load the new cog with ``[p]load mutes``. You can see the full `Mutes changelog below <important-341-1>`.
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

Core Bot
********

- Fixed an incorrect error being reported on ``[p]set name`` when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- Fixed ``[p]set nickname`` erroring when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- Fixed an ungraceful error being raised when running ``[p]traceback`` with closed DMs (:issue:`4329`)
- Fixed errors that could arise from invalid URLs in ``[p]set avatar`` (:issue:`4437`)
- Fixed an error being raised with ``[p]set nickname`` when no nickname was provided (:issue:`4451`)
- Fixed and clarified errors being raised with ``[p]set username`` (:issue:`4463`)
- Fixed an ungraceful error being raised when the output of ``[p]unload`` is larger than 2k characters (:issue:`4469`)
- Fixed an ungraceful error being raised when running ``[p]choose`` with empty options (:issue:`4499`)
- Fixed an ungraceful error being raised when a bot left a guild while a menu was open (:issue:`3902`)
- Fixed info missing on the non-embed version of ``[p]debuginfo`` (:issue:`4524`)
- Added ``[p]set api list`` to list all currently set API services, without tokens (:issue:`4370`)
- Added ``[p]set api remove`` to remove API services, including tokens (:issue:`4370`)
- Added ``[p]helpset usetick``, toggling command message being ticked when help is sent to DM (:issue:`4467`, :issue:`4075`)
- Added a default color field to ``[p]set showsettings`` (:issue:`4498`, :issue:`4497`)
- Added the datapath and metadata file to ``[p]debuginfo`` (:issue:`4524`)
- Added a list of disabled intents to ``[p]debuginfo`` (:issue:`4423`)
- Bumped discord.py dependency to version 1.5.1 (:issue:`4423`)
- Locales and regional formats can now be set in individual guilds using ``[p]set locale`` and ``[p]set regionalformat`` (:issue:`3896`, :issue:`1970`)

    - Global locale and regional format setters have been renamed to ``[p]set globallocale`` and ``[p]set globalregionalformat``

Audio
*****

- Scattered grammar and typo fixes (:issue:`4446`)
- Fixed Bandcamp playback (:issue:`4504`)
- Fixed YouTube playlist playback (:issue:`4504`)
- Fixed YouTube searching issues (:issue:`4504`)
- Fixed YouTube age restricted track playback (:issue:`4504`)
- Fixed the Audio cog not being translated when setting locale (:issue:`4492`, :issue:`4495`)
- Fixed tracks getting stuck at 0:00 after long player sessions (:issue:`4529`)
- Removed lavalink logs from being added to backup (:issue:`4453`, :issue:`4452`)
- Removed stream durations from being in queue duration (:issue:`4513`)
- Added the Global Audio API, to cut down on Youtube 429 errors and allow Spotify playback past user's quota. (:issue:`4446`)
- Added persistent queues, allowing for queues to be restored on a bot restart or cog reload (:issue:`4446`)
- Added ``[p]audioset restart``, allowing for Lavalink connection to be restarted (:issue:`4446`)
- Added ``[p]audioset autodeafen``, allowing for bot to auto-deafen itself when entering voice channel (:issue:`4446`)
- Added ``[p]audioset mycountrycode``, allowing Spotify search locale per user (:issue:`4446`)
- Added ``[p]llsetup java``, allowing for a custom Java executable path (:issue:`4446`)
- Added ``[p]llset info`` to show Lavalink settings (:issue:`4527`)
- Added ``[p]audioset logs`` to download Lavalink logs if the Lavalink server is set to internal (:issue:`4527`)

Cleanup
*******

- Allowed ``[p]cleanup self`` to work in DMs for all users (:issue:`4481`)

Custom Commands
***************

- Fixed an ungraceful error being thrown on ``[p]cc edit`` (:issue:`4325`)

Dev
***

- Added ``[p]repl pause`` to pause/resume the REPL session in the current channel (:issue:`4366`)

Economy
*******

- Added an embed option for ``[p]leaderboard`` (:issue:`4184`, :issue:`4104`)

General
*******

- Fixed issues with text not being properly URL encoded (:issue:`4024`)
- Fixed an ungraceful error occurring when a title is longer than 256 characters in ``[p]urban`` (:issue:`4474`)
- Changed "boosters" to "boosts" in ``[p]serverinfo`` to clarify what the number represents (:issue:`4507`)

Mod
***

- Added ``[p]modset mentionspam strict`` allowing for duplicated mentions to count towards the mention spam cap (:issue:`4359`)
- Added an option to ban users not in the guild to ``[p]ban`` (:issue:`4422`, :issue:`4419`)
- Added a default tempban duration for ``[p]tempban`` (:issue:`4473`, :issue:`3992`)
- Fixed nicknames not being properly stored and logged (:issue:`4131`)
- Fixed plural typos in ``[p]userinfo`` (:issue:`4397`, :issue:`4379`)
- Renamed ``[p]hackban`` to ``[p]massban``, keeping ``[p]hackban`` as an alias, allowing for multiple users to be banned at once (:issue:`4422`, :issue:`4419`)
- Moved mutes to a separate, individual cog (:issue:`3634`)

.. _important-341-1:

Mutes
*****

- Added ``[p]muteset forcerole`` to make mutes role based, instead of permission based (:issue:`3634`)
- Added an optional time argument to all mutes, to specify when the user should be unmuted (:issue:`3634`)
- Changed ``[p]mute`` to only handle serverwide muting, ``[p]mute voice`` and ``[p]mute channel`` have been moved to separate commands called ``[p]mutechannel`` and ``[p]mutevoice`` (:issue:`3634`)
- Mute commands can now take multiple user arguments, to mute multiple users at a time (:issue:`3634`)

Modlog
******

- Fixed an error being raised when running ``[p]casesfor`` and ``[p]case`` (:issue:`4415`)
- Long reasons in Modlog are now properly shortened in message content (:issue:`4541`)

Trivia Lists
************

- Fixed incorrect order of Machamp and Machoke questions (:issue:`4424`)
- Added new MLB trivia list (:issue:`4455`)
- Added new Who's That Pokémon - Gen. IV trivia list (:issue:`4434`)
- Added new Hockey trivia list (:issue:`4384`)

Warnings
********

- Fixed users being able to warn users above them in hierarchy (:issue:`4100`)
- Added bool arguments to toggle commands to improve consistency (:issue:`4409`)

Developer changelog
-------------------

| **Important:**
| #. Red now allows users to set locale per guild, which requires 3rd-party cogs to set contextual locale manually in code ran outside of command's context. See the `Core Bot changelog below <important-dev-341-1>` for more information.

.. _important-dev-341-1:

Core Bot
********

- Added API for setting contextual locales (:issue:`3896`, :issue:`1970`)

    - New function added: `redbot.core.i18n.set_contextual_locales_from_guild()`
    - Contextual locale is automatically set for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information

- Added `bot.remove_shared_api_services() <Red.remove_shared_api_services()>` to remove all keys and tokens associated with an API service (:issue:`4370`)
- Added an option to return all tokens for an API service if ``service_name`` is not specified in `bot.get_shared_api_tokens() <Red.get_shared_api_tokens()>` (:issue:`4370`)
- Added `bot.get_or_fetch_user() <Red.get_or_fetch_user()>` and `bot.get_or_fetch_member() <Red.get_or_fetch_member()>` methods (:issue:`4403`, :issue:`4402`)
- Moved ``redbot.core.checks.bot_in_a_guild()`` to `redbot.core.commands.bot_in_a_guild()` (old name has been left as an alias) (:issue:`4515`, :issue:`4510`)

Bank
****

- Bank API methods now consistently throw TypeError if a non-integer amount is supplied (:issue:`4376`)

Mod
***

- Deprecated ``redbot.core.utils.mod.is_allowed_by_hierarchy`` (:issue:`4435`)

Modlog
******

- Added an option to accept a ``discord.Object`` in case creation (:issue:`4326`)
- Added ``last_known_username`` parameter to `modlog.create_case()` function (:issue:`4326`)
- Fixed an error being raised with a deleted channel in `Case.message_content()` (:issue:`4415`)

Utility
*******

- Added `redbot.core.utils.get_end_user_data_statement()` and `redbot.core.utils.get_end_user_data_statement_or_raise()` to attempt to fetch a cog's End User Data Statement (:issue:`4404`)
- Added `redbot.core.utils.chat_formatting.quote()` to quote text in a message (:issue:`4425`)

Documentation changes
---------------------

Config
******

- Added custom group documentation and tutorial (:issue:`4416`, :issue:`2896`)

Modlog
******

- Clarified that naive ``datetime`` objects will be treated as local times for parameters ``created_at`` and ``until`` in `modlog.create_case()` (:issue:`4389`)

Other
*****

- Added guide to creating a Bot Application in Discord Developer Portal, with enabling intents (:issue:`4502`)

Miscellaneous
-------------

- Added JSON schema files for ``info.json`` files (:issue:`4375`)
- Added ``[all]`` and ``[dev]`` bundled install extras (:issue:`4443`)
- Replaced the link to the approved repository list on CogBoard and references to ``cogs.red`` with a link to new Red Index (:issue:`4439`)
- Improved documentation about arguments in command syntax (:issue:`4058`)
- Replaced a few instances of Red with the bot name in command docstrings (:issue:`4470`)
- Fixed grammar in places scattered throughout bot (:issue:`4500`)
- Properly define supported Python versions to be lower than 3.9 (:issue:`4538`)


3.4.0 (2020-08-17)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`DevilXD`, :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kablekompany`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`SharkyTheKing`, :ghuser:`thisisjvgrace`, :ghuser:`Tinonb`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. Red 3.4 comes with support for data deletion requests. Bot owners should read `red_core_data_statement` to ensure they know what information about their users is stored by the bot.
#. Debian Stretch, Fedora 30 and lower, and OpenSUSE Leap 15.0 and lower are no longer supported as they have already reached end of life.
#. There's been a change in behavior of ``[p]tempban``. Look at `Mod changelog <important-340-1>` for full details.
#. There's been a change in behavior of announcements in Admin cog. Look at `Admin changelog <important-340-2>` for full details.
#. Red 3.4 comes with breaking changes for cog developers. Look at `Developer changelog <important-340-3>` for full details.

End-user changelog
------------------

Core Bot
********

- Added per-guild cog disabling (:issue:`4043`, :issue:`3945`)

    - Bot owners can set the default state for a cog using ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands
    - Guild owners can enable/disable cogs for their guild using ``[p]command disablecog`` and ``[p]command enablecog`` commands
    - Cogs disabled in the guild can be listed with ``[p]command listdisabledcogs``

- Added support for data deletion requests; see `red_core_data_statement` for more information (:issue:`4045`)
- Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)
- ``[p]licenseinfo`` now has a 3 minute cooldown to prevent a single user from spamming channel by using it (:issue:`4110`)
- Added ``[p]helpset showsettings`` command (:issue:`4013`, :issue:`4022`)
- Updated Red's emoji usage to ensure consistent rendering accross different devices (:issue:`4106`, :issue:`4105`, :issue:`4127`)
- Whitelist and blacklist are now called allowlist and blocklist. Old names have been left as aliases (:issue:`4138`)

.. _important-340-2:

Admin
*****

- ``[p]announce`` will now only send announcements to guilds that have explicitly configured text channel to send announcements to using ``[p]announceset channel`` command (:issue:`4088`, :issue:`4089`)

Downloader
**********

- ``[p]cog info`` command now shows end user data statement made by the cog creator (:issue:`4169`)
- ``[p]cog update`` command will now notify the user if cog's end user data statement has changed since last update (:issue:`4169`)

.. _important-340-1:

Mod
***

- ``[p]tempban`` now respects default days setting (``[p]modset defaultdays``) (:issue:`3993`)
- Users can now set mention spam triggers which will warn or kick the user. See ``[p]modset mentionspam`` for more information (:issue:`3786`, :issue:`4038`)
- ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)

ModLog
******

- Added timestamp to text version of ``[p]casesfor`` and ``[p]case`` commands (:issue:`4118`, :issue:`4137`)

Streams
*******

- Stream alerts will no longer make roles temporarily mentionable if bot has "Mention @everyone, @here, and All Roles" permission in the channel (:issue:`4182`)
- Mixer service has been closed and for that reason we've removed support for it from the cog (:issue:`4072`)
- Hitbox commands have been renamed to smashcast (:issue:`4161`)
- Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

Trivia Lists
************

- Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)

.. _important-340-3:

Developer changelog
-------------------

| **Important:**
| #. Red now offers cog disabling API, which should be respected by 3rd-party cogs in guild-related actions happening outside of command's context. See the `Core Bot changelog below <important-dev-340-1>` for more information.
| #. Red now provides data request API, which should be supported by all 3rd-party cogs. See the changelog entries in the `Core Bot changelog below <important-dev-340-1>` for more information.

Breaking changes
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

Core Bot
********

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
- `bot.ignored_channel_or_guild() <Red.ignored_channel_or_guild()>` now accepts `discord.Message` objects (:issue:`4077`)
- `commands.NoParseOptional <NoParseOptional>` is no longer provisional and is now fully supported part of API (:issue:`4142`)
- Red no longer fails to run subcommands of a command group allowed or denied by permission hook (:issue:`3956`)
- Autohelp in group commands is now sent *after* invoking the group, which allows before invoke hooks to prevent autohelp from getting triggered (:issue:`4129`)
- RPC functionality no longer makes Red hang for a minute on shutdown (:issue:`4134`, :issue:`4143`)

Vendored packages
*****************

- Updated ``discord.ext.menus`` vendor (:issue:`4167`)

Utility Functions
*****************

- `humanize_list()` now accepts ``locale`` and ``style`` keyword arguments. See its documentation for more information (:issue:`2982`)
- `humanize_list()` is now properly localized (:issue:`2906`, :issue:`2982`)
- `humanize_list()` now accepts empty sequences (:issue:`2982`)


Documentation changes
---------------------

- Removed install instructions for Debian Stretch (:issue:`4099`)
- Added admin user guide (:issue:`3081`)
- Added alias user guide (:issue:`3084`)
- Added bank user guide (:issue:`4149`)


Miscellaneous
-------------

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)
- ``[p]set nickname``, ``[p]set serverprefix``, ``[p]streamalert``, and ``[p]streamset`` commands now can be run by users with permissions related to the actions they're making (:issue:`4109`)
- `bordered()` now uses ``+`` for corners if keyword argument ``ascii_border`` is set to `True` (:issue:`4097`)
- Fixed timestamp storage in few places in Red (:issue:`4017`)

3.3.12 (2020-08-18)
===================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`douglas-cpp`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MeatyChunks`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

End-user changelog
------------------

Core Bot
********

- Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)

Mod
***

- ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)

Streams
*******

- Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

Trivia Lists
************

- Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)


Miscellaneous
-------------

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)


3.3.11 (2020-08-10)
===================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`Flame`, :ghuser:`jack1142`, :ghuser:`MeatyChunks`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

End-user changelog
------------------

Audio
*****

- Audio should now work again on all voice regions (:issue:`4162`, :issue:`4168`)
- Removed an edge case where an unfriendly error message was sent in Audio cog (:issue:`3879`)

Cleanup
*******

- Fixed a bug causing ``[p]cleanup`` commands to clear all messages within last 2 weeks when ``0`` is passed as the amount of messages to delete (:issue:`4114`, :issue:`4115`)

CustomCommands
**************

- ``[p]cc show`` now sends an error message when command with the provided name couldn't be found (:issue:`4108`)

Downloader
**********

- ``[p]findcog`` no longer fails for 3rd-party cogs without any author (:issue:`4032`, :issue:`4042`)
- Update commands no longer crash when a different repo is added under a repo name that was once used (:issue:`4086`)

Permissions
***********

- ``[p]permissions removeserverrule`` and ``[p]permissions removeglobalrule`` no longer error when trying to remove a rule that doesn't exist (:issue:`4028`, :issue:`4036`)

Warnings
********

- ``[p]warn`` now sends an error message (instead of no feedback) when an unregistered reason is used by someone who doesn't have Administrator permission (:issue:`3839`, :issue:`3840`)


3.3.10 (2020-07-09)
===================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`

End-user changelog
------------------

Audio
*****

- Added information about internally managed jar to ``[p]audioset info`` (:issue:`3915`)
- Updated to Lavaplayer 1.3.50
- Twitch playback and YouTube searching should be functioning again.

Core Bot
********

- Fixed delayed help when ``[p]set deletedelay`` is enabled (:issue:`3884`, :issue:`3883`)
- Bumped the Discord.py requirement from 1.3.3 to 1.3.4 (:issue:`4053`)
- Added settings view commands for nearly all cogs. (:issue:`4041`)
- Added more strings to be fully translatable by i18n. (:issue:`4044`)

Downloader
**********

- Added ``[p]cog listpinned`` subcommand to see currently pinned cogs (:issue:`3974`)
- Fixed unnecessary typing when running downloader commands (:issue:`3964`, :issue:`3948`)
- Added embed version of ``[p]findcog`` (:issue:`3965`, :issue:`3944`)
- Fixed ``[p]findcog`` not differentiating between core cogs and local cogs(:issue:`3969`, :issue:`3966`)

Filter
******

- Added ``[p]filter list`` to show filtered words, and removed DMs when no subcommand was passed (:issue:`3973`)

Image
*****

- Updated instructions for obtaining and setting the GIPHY API key (:issue:`3994`)

Mod
***

- Added option to delete messages within the passed amount of days with ``[p]tempban`` (:issue:`3958`)
- Added the ability to permanently ban a temporary banned user with ``[p]hackban`` (:issue:`4025`)
- Fixed the passed reason not being used when using ``[p]tempban`` (:issue:`3958`)
- Fixed invite being sent with ``[p]tempban`` even when no invite was set (:issue:`3991`)
- Prevented an issue whereby the author may lock him self out of using the bot via whitelists (:issue:`3903`)
- Reduced the number of API calls made to the storage APIs (:issue:`3910`)

Permissions
***********

- Uploaded YAML files now accept integer commands without quotes (:issue:`3987`, :issue:`3185`)
- Uploaded YAML files now accept command rules with empty dictionaries (:issue:`3987`, :issue:`3961`)

Streams
*******

- Fixed streams cog sending multiple owner notifications about twitch secret not set (:issue:`3901`, :issue:`3587`)
- Fixed old bearer tokens not being invalidated when the API key is updated (:issue:`3990`, :issue:`3917`)

Trivia Lists
************

- Fixed URLs in ``whosthatpokemon`` (:issue:`3975`, :issue:`3023`)
- Fixed trivia files ``leagueults`` and ``sports`` (:issue:`4026`)
- Updated ``greekmyth`` to include more answer variations (:issue:`3970`)
- Added new ``lotr`` trivia list (:issue:`3980`)
- Added new ``r6seige`` trivia list (:issue:`4026`)


Developer changelog
-------------------

- Added the utility functions ``map``, ``find``, and ``next`` to ``AsyncIter`` (:issue:`3921`, :issue:`3887`)
- Updated deprecation times for ``APIToken``, and loops being passed to various functions to the first minor release (represented by ``X`` in ``3.X.0``) after 2020-08-05 (:issue:`3608`)
- Updated deprecation warnings for shared libs to reflect that they have been moved for an undefined time (:issue:`3608`)
- Added new ``discord.com`` domain to ``INVITE_URL_RE`` common filter (:issue:`4012`)
- Fixed incorrect role mention regex in ``MessagePredicate`` (:issue:`4030`)
- Vendor the ``discord.ext.menus`` module (:issue:`4039`)


Miscellaneous
-------------

- Improved error responses for when Modlog and Autoban on mention spam were already disabled (:issue:`3951`, :issue:`3949`)
- Clarified that ``[p]embedset user`` only affects commands executed in DMs (:issue:`3972`, :issue:`3953`)
- Added link to Getting Started guide if the bot was not in any guilds (:issue:`3906`)
- Fixed exceptions being ignored or not sent to log files in special cases (:issue:`3895`)
- Added the option of using dots in the instance name when creating your instances (:issue:`3920`)
- Added a confirmation when using hyphens in instance names to discourage the use of them (:issue:`3920`)
- Fixed migration owner notifications being sent even when migration was not necessary (:issue:`3911`. :issue:`3909`)
- Fixed commands being translated where they should not be (:issue:`3938`, :issue:`3919`)
- Fixed grammar errors and added full stopts in ``core_commands.py`` (:issue:`4023`)


3.3.9 (2020-06-12)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`Predeactor`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Bot owners can no longer restrict access to some commands in Permissions cog using global permissions rules. Look at `Permissions changelog <important-339-2>` for full details.
#. There's been a change in behavior of warning messages. Look at `Warnings changelog <important-339-1>` for full details.

End-user changelog
------------------

Security
********

**NOTE**: If you can't update immediately, we recommend disabling the affected command until you can.

- **Mod** - ``[p]tempban`` now properly respects Discord's hierarchy rules (:issue:`3957`)

Core Bot
********

- ``[p]info`` command can now be used when bot doesn't have Embed Links permission (:issue:`3907`, :issue:`3102`)
- Fixed ungraceful error that happened in ``[p]set custominfo`` when provided text was too long (:issue:`3923`)
- Red's start up message now shows storage type (:issue:`3935`)

Audio
*****

- Audio now properly ignores streams when max length is enabled (:issue:`3878`, :issue:`3877`)
- Commands that should work in DMs no longer error (:issue:`3880`)

Filter
******

- Fixed behavior of detecting quotes in commands for adding/removing filtered words (:issue:`3925`)

.. _important-339-2:

Permissions
***********

- **Both global and server rules** can no longer prevent guild owners from accessing commands for changing server rules. Bot owners can still use ``[p]command disable`` if they wish to completely disable any command in Permissions cog (:issue:`3955`, :issue:`3107`)

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

Warnings
********

- Warnings sent to users don't show the moderator who warned the user by default now. Newly added ``[p]warningset showmoderators`` command can be used to switch this behaviour (:issue:`3781`)
- Warn channel functionality has been fixed (:issue:`3781`)


Developer changelog
-------------------

Core Bot
********

- Added `bot.set_prefixes() <Red.set_prefixes()>` method that allows developers to set global/server prefixes (:issue:`3890`)


Documentation changes
---------------------

- Added Oracle Cloud to free hosting section in :ref:`host-list` (:issue:`3916`)

Miscellaneous
-------------

- Added missing help message for Downloader, Reports and Streams cogs (:issue:`3892`)
- **Core Bot** - cooldown in ``[p]contact`` no longer applies when it's used without any arguments (:issue:`3942`)
- **Core Bot** - improved instructions on obtaining user ID in help of ``[p]dm`` command (:issue:`3946`)
- **Alias** - ``[p]alias global`` group, ``[p]alias help``, and ``[p]alias show`` commands can now be used in DMs (:issue:`3941`, :issue:`3940`)
- **Audio** - Typo fix (:issue:`3889`, :issue:`3900`)
- **Audio** - Fixed ``[p]audioset autoplay`` being available in DMs (:issue:`3899`)
- **Bank** - ``[p]bankset`` now displays bank's scope (:issue:`3954`)
- **Mod** - Preemptive fix for d.py 1.4 (:issue:`3891`)


3.3.8 (2020-05-29)
===========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Bakersbakebread`, :ghuser:`DariusStClair`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`qaisjp`, :ghuser:`Tobotimus`

End-user changelog
------------------

Core Bot
********

- Important fixes to how PostgreSQL data backend saves data in bulks (:issue:`3829`)
- Fixed ``[p]localwhitelist`` and ``[p]localblacklist`` commands (:issue:`3857`)
- Red now includes information on how to update when sending information about being out of date (:issue:`3744`)
- Using backslashes in bot's username/nickname no longer causes issues (:issue:`3826`, :issue:`3825`)

Admin
*****

- Fixed server lock (:issue:`3815`, :issue:`3814`)

Alias
*****

- Added pagination to ``[p]alias list`` and ``[p]alias global list`` to avoid errors for users with a lot of aliases (:issue:`3844`, :issue:`3834`)
- ``[p]alias help`` should now work more reliably (:issue:`3864`)

Audio
*****

- Twitch playback is functional once again (:issue:`3873`)
- Recent errors with YouTube playback should be resolved (:issue:`3873`)
- Added new option (settable with ``[p]audioset lyrics``) that makes Audio cog prefer (prioritize) tracks with lyrics (:issue:`3519`)
- Added global daily (historical) queues (:issue:`3518`)
- Added ``[p]audioset countrycode`` that allows to set the country code for spotify searches (:issue:`3528`)
- Fixed ``[p]local search`` (:issue:`3528`, :issue:`3501`)
- Local folders with special characters should work properly now (:issue:`3528`, :issue:`3467`)
- Audio no longer fails to take the last spot in the voice channel with user limit (:issue:`3528`)
- ``[p]local play`` no longer enqueues tracks from nested folders (:issue:`3528`)
- Fixed ``[p]playlist dedupe`` not removing tracks (:issue:`3518`)
- ``[p]disconnect`` now allows to disconnect if both DJ mode and voteskip aren't enabled (:issue:`3502`, :issue:`3485`)
- Many UX improvements and fixes, including, among other things:

  - Creating playlists without explicitly passing ``-scope`` no longer causes errors (:issue:`3500`)
  - ``[p]playlist list`` now shows all accessible playlists if ``--scope`` flag isn't used (:issue:`3518`)
  - ``[p]remove`` now also accepts a track URL in addition to queue index (:issue:`3201`)
  - ``[p]playlist upload`` now accepts a playlist file uploaded in the message with a command (:issue:`3251`)
  - Commands now send friendly error messages for common errors like lost Lavalink connection or bot not connected to voice channel (:issue:`3503`, :issue:`3528`, :issue:`3353`, :issue:`3712`)

CustomCommands
**************

- ``[p]customcom create`` no longer allows spaces in custom command names (:issue:`3816`)

Mod
***

- ``[p]userinfo`` now shows default avatar when no avatar is set (:issue:`3819`)

Modlog
******

- Fixed (again) ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3805`, :issue:`3784`, :issue:`3778`)

Permissions
***********

- Commands for settings ACL using yaml files now properly works on PostgreSQL data backend (:issue:`3829`, :issue:`3796`)

Warnings
********

- Warnings cog no longer allows to warn bot users (:issue:`3855`, :issue:`3854`)


Developer changelog
-------------------

| **Important:**
| If you're using RPC, please see the full annoucement about current state of RPC in main Red server
  `by clicking here <https://discord.com/channels/133049272517001216/411381123101491200/714560168465137694>`__.


Core Bot
********

- Red now inherits from `discord.ext.commands.AutoShardedBot` for better compatibility with code expecting d.py bot (:issue:`3822`)
- Libraries using ``pkg_resources`` (like ``humanize`` or ``google-api-python-client``) that were installed through Downloader should now work properly (:issue:`3843`)
- All bot owner IDs can now be found under ``bot.owner_ids`` attribute (:issue:`3793`)

  -  Note: If you want to use this on bot startup (e.g. in cog's initialisation), you need to await ``bot.wait_until_red_ready()`` first


Documentation changes
---------------------

- Added information about provisional status of RPC (:issue:`3862`)
- Revised install instructions (:issue:`3847`)
- Improved navigation in `document about updating Red <update_red>` (:issue:`3856`, :issue:`3849`)


Miscellaneous
-------------

- Few clarifications and typo fixes in few command help docstrings (:issue:`3817`, :issue:`3823`, :issue:`3837`, :issue:`3851`, :issue:`3861`)
- **Downloader** - Downloader no longer removes the repo when it fails to load it (:issue:`3867`)


3.3.7 (2020-04-28)
==================

This is a hotfix release fixing issue with generating messages for new cases in Modlog.


3.3.6 (2020-04-27)
==================

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

- Updated ``leagueoflegends`` list with new changes to League of Legends (`b8ac70e <https://github.com/Cog-Creators/Red-DiscordBot/commit/b8ac70e59aa1328f246784f14f992d6ffe00d778>`__)


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


3.3.5 (2020-04-09)
==================

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


3.3.4 (2020-04-05)
==================

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


3.3.3 (2020-03-28)
==================

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
- Permissions for commands in Bank, Economy and Trivia cogs can now be overridden by Permissions cog (:issue:`3672`, :issue:`3233`)
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

- Fixed install instructions for Mac (:issue:`3675`, :issue:`3436`)
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


3.3.2 (2020-02-28)
==================

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


3.3.1 (2020-02-05)
==================

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

3.3.0 (2020-01-26)
==================

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

3.2.3 (2020-01-17)
==================

Core Bot Changes
----------------

- Further improvements have been made to bot startup and shutdown.
- Prefixes are now cached for performance.
- Added the means for cog creators to use a global preinvoke hook.
- The bot now ensures it has at least the bare neccessary permissions before running commands.
- Deleting instances works as intended again.
- Sinbad stopped fighting it and embraced the entrypoint madness.

Core Commands
-------------

- The servers command now also shows the ids.

Admin Cog
---------

- The selfrole command now has reasonable expectations about hierarchy.

Help Formatter
--------------

- ``[botname]`` is now replaced with the bot's display name in help text.
- New features added for cog creators to further customize help behavior.
  
  - Check out our command reference for details on new ``format_help_for_context`` method.
- Embed settings are now consistent.

Downloader
----------

- Improved a few user facing messages.
- Added pagination of output on cog update.
- Added logging of failures.

Docs
----

There's more detail to the below changes, so go read the docs.
For some reason, documenting documentation changes is hard.

- Added instructions about git version.
- Clarified instructions for installation and update.
- Added more details to the API key reference.
- Fixed some typos and versioning mistakes.


Audio
-----

Draper did things.

- No seriously, Draper did things.
- Wait you wanted details? Ok, I guess we can share those.
- Audio properly disconnects with autodisconnect, even if notify is being used.
- Symbolic links now work as intended for local tracks.
- Bump play now shows the correct time till next track.
- Multiple user facing messages have been made more correct.

3.2.2 (2020-01-10)
==================

Hotfixes
--------

- Fix Help Pagination issue

Docs
----

- Correct venv docs


3.2.1 (2020-01-10)
==================

Hotfixes
--------

- Fix Mongo conversion from being incorrectly blocked
- Fix announcer not creating a message for success feedback
- Log an error with creating case types rather than crash


3.2.0 (2020-01-09)
==================

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

3.1.1 (2019-05-15)
==================

This is a hotfix release fixing issues related to fuzzy command search that were happening with the new help formatter.


3.1.0 (2019-05-15)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`calebj`, :ghuser:`DiscordLiz`, :ghuser:`EgonSpengler`, :ghuser:`entchen66`, :ghuser:`FixedThink`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`lionirdeadman`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`NIXC`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Seputaes`, :ghuser:`Sitryk`, :ghuser:`tekulvw`, :ghuser:`Tobotimus`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`zephyrkul`

End-user changelog
------------------

Core Bot
********

- Error messages about cooldowns will now show more friendly representation of cooldown's expiration time (:issue:`2412`)
- Cooldown messages are now auto-deleted after cooldown expiration expired (:issue:`2469`)
- Fixed local blacklist/whitelist management commands (:issue:`2531`)
- ``[p]set locale`` now only accepts actual locales (:issue:`2553`)
- ``[p]listlocales`` now includes ``en-US`` locale (:issue:`2553`)
- ``redbot --version`` will now give you current version of Red (:issue:`2567`)
- Redesigned help and its formatter (:issue:`2628`)
- Changed default locale from ``en`` to ``en-US`` (:issue:`2642`)
- Added new ``[p]datapath`` command that prints the bot's data path (:issue:`2652`)
- Added ``redbot-setup convert`` command which can be used to convert between data backends (:issue:`2579`)
- Updated Mongo driver to support large guilds (:issue:`2536`)
- Fixed the list of available extras in the ``redbot-launcher`` (:issue:`2588`)
- Backup support for Mongo is currently broken (:issue:`2579`)

Audio
*****

- Add Spotify support (:issue:`2328`)
- Play local folders via text command (:issue:`2457`)
- Change pause to a toggle (:issue:`2461`)
- Remove aliases (:issue:`2462`)
- Add track length restriction (:issue:`2465`)
- Seek command can now seek to position (:issue:`2470`)
- Add option for dc at queue end (:issue:`2472`)
- Emptydisconnect and status refactor (:issue:`2473`)
- Queue clean and queue clear addition (:issue:`2476`)
- Fix for audioset status (:issue:`2481`)
- Playlist download addition (:issue:`2482`)
- Add songs when search-queuing (:issue:`2513`)
- Match v2 behavior for channel change (:issue:`2521`)
- Bot will no longer complain about permissions when trying to connect to user-limited channel, if it has "Move Members" permission (:issue:`2525`)
- Fix issue on audiostats command when more than 20 servers to display (:issue:`2533`)
- Fix for prev command display (:issue:`2556`)
- Fix for localtrack playing (:issue:`2557`)
- Fix for playlist queue when not playing (:issue:`2586`)
- Track search and append fixes (:issue:`2591`)
- DJ role should ask for a role (:issue:`2606`)

DataConverter
*************

- It's dead jim (Removal) (:issue:`2554`)

Downloader
**********

- Fixed bug, that caused Downloader to include submodules on cog list (:issue:`2590`)
- The error message sent by ``[p]cog install`` when required libraries fail to install is now properly formatted (:issue:`2576`)
- The ``[p]cog uninstall`` command will now remove cog from installed cogs list even if it can't find the cog in install path anymore (:issue:`2595`)
- The ``[p]cog install`` command will not allow to install cogs which aren't suitable for installed version of Red anymore (:issue:`2605`)
- The ``[p]cog install`` command will now tell the user that cog has to be loaded after the install (:issue:`2523`)
- The ``[p]cog uninstall`` command allows to uninstall multiple cogs now (:issue:`2592`)

Filter
******

- Significantly improved performance of Filter cog on large servers (:issue:`2509`)

Mod
***

- Fixed ``[p]ban`` not allowing to omit ``days`` argument (:issue:`2602`)
- Added the command ``[p]voicekick`` to kick members from a voice channel with optional modlog case (:issue:`2639`)
- Admins can now decide how many times message has to be repeated before cog's ``deleterepeats`` functionality removes it (:issue:`2437`)

Permissions
***********

- Removed ``[p]p`` alias for ``[p]permissions`` command (:issue:`2467`)

Streams
*******

- Added support for setting custom stream alert messages per guild (:issue:`2600`)
- Added ability to exclude Twitch stream reruns (:issue:`2620`)
- Twitch stream reruns are now marked as reruns in embed title (:issue:`2620`)

Trivia Lists
************

- Fixed dead image link for Sao Tome and Principe flag in ``worldflags`` trivia (:issue:`2540`)

Developer changelog
-------------------

Core Bot
********

- Red is now no longer vendoring discord.py and installs it from PyPI (:issue:`2587`)
- Upgraded discord.py dependency to version 1.0.1 (:issue:`2587`)
- Usage of ``yaml.load`` will now warn about its security issues (:issue:`2326`)
- Added a ``on_message_without_command`` event that is dispatched when bot gets an event for a message that doesn't contain a command (:issue:`2338`)

Config
******

- Introduced `Config.init_custom()` method (:issue:`2545`)
- We now record custom group primary key lengths in the core config object (:issue:`2550`)
- Migrated internal UUIDs to maintain cross platform consistency (:issue:`2604`)

Downloader
**********

- Cog Developers now have to use ``min_bot_version`` key instead of ``bot_version`` to specify minimum version of Red supported by the cog in ``info.json``, see more information in :ref:`info-json-format` (:issue:`2605`)
- Added ``max_bot_version`` key to ``info.json`` that allows to specify maximum supported version of Red supported by the cog in ``info.json``, see more information in :ref:`info-json-format`. (:issue:`2605`)

Utility Functions
*****************

- Fixed spelling of the `Tunnel`'s method from ``files_from_attatch()`` to `files_from_attach() <Tunnel.files_from_attach()>`; old name was left for backwards compatibility (:issue:`2496`)
- Fixed behavior of `Tunnel.react_close()` - now when tunnel closes, the message will be sent to the other end (:issue:`2507`)
- Added `chat_formatting.humanize_timedelta()` (:issue:`2412`)
- Improved error handling of empty lists in `chat_formatting.humanize_list()` (:issue:`2597`)


3.0.2 (2019-02-24)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Tobotimus`, :ghuser:`ZeLarpMaster`

End-user changelog
------------------

- **Permissions** - Fixed rules loading for cogs (`431cdf1 <https://github.com/Cog-Creators/Red-DiscordBot/commit/431cdf1ad4247fbe40f940e39bac4c919b470937>`__)
- **Trivia Lists** - Fixed a typo in ``cars`` trivia (:issue:`2475`)


3.0.1 (2019-02-17)
==================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`calebj`, :ghuser:`DiscordLiz`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Redjumpman`, :ghuser:`Tobotimus`, :ghuser:`Twentysix26`, :ghuser:`ZeLarpMaster`, :ghuser:`zephyrkul`

End-user changelog
------------------

Core Bot
********

- Messages sent interactively (i.e. prompting user whether they would like to view the next message) now no longer cause errors if bot's prompt message gets removed by other means (:issue:`2380`, :issue:`2447`)
- Fixed error in ``[p]servers`` command that was happening when bot's prompt message was deleted before the prompt time was over (:issue:`2400`)
- Improve some of the core commands to not require double quotes for arguments with spaces, if they're the last argument required by the command (:issue:`2407`)
- Using ``[p]load`` command now sends help message when it's used without arguments (:issue:`2432`)
- Fixed behavior of CLI arguments in ``redbot-launcher`` (:issue:`2432`)

Audio
*****

- Fixed issues with setting external Lavalink (:issue:`2306`, :issue:`2460`)
- Audio now cleans up zombie players from guilds it's no longer in (:issue:`2414`)

Downloader
**********

- Fixed issues with cloning that happened if instance's data path had spaces (:issue:`2421`)
- The ``[p]pipinstall`` command now sends help message when it's used without arguments (`eebed27 <https://github.com/Cog-Creators/Red-DiscordBot/commit/eebed27fe76aa5b51cfa38ac9a35bd182d881352>`__)

Mod
***

- ``[p]userinfo`` now accounts for guild's lurkers (:issue:`2406`, :issue:`2426`)
- Usernames and nicknames listed in ``[p]names`` and ``[p]userinfo`` commands now have the spoiler markdown escaped (:issue:`2401`)

Modlog
******

- Usernames listed in modlog cases now have the spoiler markdown escaped (:issue:`2401`)

Permissions
***********

- Fixed rule precedence issues for default rules (:issue:`2313`, :issue:`2422`)

Warnings
********

- Members can now also be passed with username, nickname, or user mention to ``[p]warnings`` and ``[p]unwarn`` commands (:issue:`2403`, :issue:`2404`)

Developer changelog
-------------------

Utility Functions
*****************

- ``MessagePredicate.lower_contained_in()`` now actually lowers the message content before trying to match (:issue:`2399`)
- Added `escape_spoilers()` and `escape_spoilers_and_mass_mentions()` methods for escaping strings with spoiler markdown (:issue:`2401`)


3.0.0 (2019-01-28)
==================

First stable release of Red V3.
Changelogs for this and previous versions can be found on `our GitHub releases page <https://github.com/Cog-Creators/Red-DiscordBot/releases?after=3.0.1>`__.
