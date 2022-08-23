.. 3.4.x Changelogs

Redbot 3.4.18 (2022-08-15)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`RheingoldRiver`

Read before updating
--------------------

#. openSUSE Leap 15.2 is no longer supported as it has already reached its end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    - Red 3.4.18 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.4.0_1350>`__.
    - We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.18/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.


End-user changelog
------------------

Core Bot
********

- openSUSE Leap 15.2 is no longer supported as it has already reached its end of life (:issue:`5777`)

Audio
*****

- Addressed a cipher change that made it impossible to find tracks (:issue:`5822`)
- Fixed an issue with ``[p]llset external`` making the bot completely unresponsive when switching to an external Lavalink server (:issue:`5804`, :issue:`5828`)


Documentation changes
---------------------

- Updated the screenshot in `bot_application_guide` to include the message content intent (:issue:`5798`)
- Unpinned Temurin version on Windows as a fixed version is now available (:issue:`5815`)


Redbot 3.4.17 (2022-06-07)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`ltzmax`, :ghuser:`matcha19`, :ghuser:`mina9999`, :ghuser:`ponte-vecchio`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`untir-l`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Fedora 34 is no longer supported as it has already reached its end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.17 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.4.0_1347>`__.


End-user changelog
------------------

Core Bot
********

- Fedora 33 is no longer supported as it has already reached its end of life (:issue:`5701`)
- Added instructions on how to respond to the message received from ``[p]contact`` in the embed footer of the message sent to the bot owner (:issue:`5528`, :issue:`5529`)
- Updated ``[p]servers`` command to escape Discord markdown in server names (:issue:`5696`, :issue:`5744`)
- Fixed a bug that prevented users from changing the name and data location with ``redbot --edit`` command (:issue:`5545`, :issue:`5540`, :issue:`5541`)
- Fixed grammar in the ``[p]uptime`` command (:issue:`5596`)

Audio
*****

- Added timestamps to all embeds sent by Audio cog (:issue:`5632`)
- Improved handling of voice connection close codes received from Discord (:issue:`5712`)
- Fixed plain word YT searching with ``[p]play`` and ``[p]search`` commands (:issue:`5712`)
- Fixed YT age-restricted track playback (:issue:`5712`)
- Fixed the cog not sending any Track Error message on track decoding errors (:issue:`5716`)
- Fixed the ``UnboundLocalError`` exception happening when using ``[p]playlist list`` with an empty playlist (:issue:`5378`, :issue:`5394`)

Downloader
**********

- Added information about the commit hash at which the cog is pinned in the output of ``[p]cog listpinned`` command (:issue:`5551`, :issue:`5563`)

Filter
******

- Fixed a potential memory leak in Filter cog (:issue:`5578`)

General
*******

- Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`5655`)

Mod
***

- Updated Red's ban commands to address the breaking change that Discord made in their ban list API endpoint (:issue:`5656`)

Modlog
******

- Modlog's automated case creation for bans now properly checks that the guild is available before further processing (:issue:`5647`)

Mutes
*****

- Added proper error handling for VERY long durations in mute commands (:issue:`5605`)

Permissions
***********

- Updated ``[p]permissions acl setglobal`` and ``[p]permissions acl setserver`` to allow sending the file in a follow-up message (:issue:`5473`, :issue:`5685`)
- ``[p]permissions canrun`` now prepends an emoji to the response to better differentiate between the positive and negative results (:issue:`5711`)

Trivia
******

- Allowed passing ``use_spoilers`` setting in the CONFIG section of the trivia list file (:issue:`5566`)

Trivia Lists
************

- Added a trivia list for the FIFA World Cup with questions based on hosts, placements, venues, continental confederations, number of participants, top goal scorers, qualification shocks, and more (:issue:`5639`)
- Updated ``geography`` trivia list with up-to-date answers and removed questions that lack sources for their claimed answers (:issue:`5638`)
- Updated Kazakhstan's capital city in the ``worldcapitals`` trivia list (:issue:`5598`, :issue:`5599`)
- Fixed spelling error in the answer to one of the questions in ``computers`` trivia list (:issue:`5587`, :issue:`5588`)


Developer changelog
-------------------

- Updated ``discord.ext.menus`` vendor (:issue:`5579`)


Documentation changes
---------------------

- Added CentOS Stream 9, RHEL 9, Alma Linux 9, Oracle Linux 9, and Rocky Linux 9 install guides (:issue:`5537`, :issue:`5721`)
- Added Ubuntu 22.04 install guide (:issue:`5720`)
- Changed the recommended operating system for hosting Red from Ubuntu 20.04 LTS to Ubuntu 22.04 LTS (:issue:`5720`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5719`)
- Replaced install instructions for discontinued AdoptOpenJDK package with Temurin 11 package in the macOS install guide (:issue:`5718`)
- Updated Visual Studio Build Tools version in Windows install guide (:issue:`5702`)
- Updated systemd guide to use the absolute path to ``which`` command to avoid triggering shell aliases on some OSes (:issue:`5547`)
- Emphasized lines that contain text that needs to be replaced by the user (:issue:`5548`)
- Prevented Google and other search engines from indexing versioned documentation (:issue:`5549`)
- Pinned Temurin version on Windows until a fixed version becomes available (:issue:`5717`)
- Fixed git installation instructions in CentOS 7 install guide (:issue:`5700`)


Redbot 3.4.16 (2021-12-31)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`PredaaA`

This is a hotfix release fixing issues with invite URL API that caused
``[p]invite`` command and ``CORE__INVITE_URL`` RPC method to not work.

End-user changelog
------------------

- **Core Bot** - Fixed ``[p]invite`` command (:issue:`5517`)


Developer changelog
-------------------

- Fixed ``CORE__INVITE_URL`` RPC method (:issue:`5517`)


Documentation changes
---------------------

- Changed Arch install guide to temporarily use ``python39`` AUR package instead of ``python`` package as Red does not currently support Python 3.10 (:issue:`5518`)


Redbot 3.4.15 (2021-12-31)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`Arman0334`, :ghuser:`Crossedfall`, :ghuser:`Dav-Git`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Jan200101`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`laggron42`, :ghuser:`ltzmax`, :ghuser:`Parnassius`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`RasmusWL`, :ghuser:`sravan1946`, :ghuser:`Stonedestroyer`, :ghuser:`the-krak3n`, :ghuser:`Tobotimus`, :ghuser:`vertyco`, :ghuser:`Vexed01`, :ghuser:`WreckRox`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Fedora 33 and CentOS 8 are no longer supported as they have already reached end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.15 uses a new Lavalink jar that you MUST manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.4.0_1275>`__ to be able to continue using Audio.


End-user changelog
------------------

Core Bot
********

- Added new CLI options for non-interactive usage of ``redbot-setup`` (:issue:`2396`, :issue:`5448`)

    See output of ``redbot-setup --help`` for more information.

- JSON is now more strongly recommended and is used by default for new instances in ``redbot-setup`` (:issue:`5448`)
- The embed setting for ``[p]help`` command set with ``[p]embedset command`` will now affect all help messages, not just the ones sent when invoking ``[p]help`` command directly (:issue:`5452`)
- ``[p]traceback`` command now indicates that it DMed the command caller with a tick reaction (:issue:`5353`)
- Improved ``[p]helpset showaliases`` responses (:issue:`5376`)
- Added plural forms to the responses of ``[p]leave`` command (:issue:`5391`)
- Fedora 33 and CentOS 8 are no longer supported as they have already reached end of life (:issue:`5440`)
- Corrected usage examples in help of ``[p]set api`` and ``[p]set api remove`` (:issue:`5444`)
- Updated prefix length limit to ``25`` to allow setting bot mention as a prefix (:issue:`5476`)
- Confirmation prompts (accepting "yes/no" or "I agree" as the answer) no longer wrongfully translate the answer that needs to be sent when only English answers are accepted by the bot (:issue:`5363`, :issue:`5364`, :issue:`5404`)
- Fixed short help for some of the commands in Core Red (:issue:`5502`)
- Fixed issues with rendering of modlog cases with usernames written in a right-to-left language (:issue:`5422`)
- Fixed an issue with instance backup failing for non-JSON storage backends (:issue:`5315`)
- Running Red with ``--no-instance`` CLI flag no longer fails when no instance was ever created by the user (:issue:`5415`, :issue:`5416`)
- ``[p]command enable guild`` and ``[p]command disable guild`` commands no longer error out for commands that *only* check for user permissions, not caller's roles (:issue:`5477`)

Admin
*****

- Added ``[p]selfroleset clear`` command which can be used to clear the list of available selfroles in the server (:issue:`5387`)

Audio
*****

- Added native Mac M1 support for Java runtimes supporting Mac M1 (:issue:`5474`)
- Enabled JDA-NAS on all system architectures which should limit stuttering/buffering issues on some machines (:issue:`5474`)
- The bot will now disconnect from the voice channel when all members are bots if the auto-disconnect setting is enabled (:issue:`5421`)
- Fixed an issue with resuming playback after changing voice channels (:issue:`5170`)
- Fixed issues with Soundcloud private playlists and mobile links (:issue:`5474`)
- Fixed searching music with some of the queries containing quotes or backslashes (:issue:`5474`)
- Fixed an exception caused by unavailable YT tracks in Mix playlists (:issue:`5474`)
- Fixed ``IndexError`` in ``[p]queue`` command which occurred when the user provides negative integer as the page number (:issue:`5429`)

Cleanup
*******

- Restricted ``[p]cleanupset notify`` to only be invokable in server channels (:issue:`5466`)

Custom Commands
***************

- Added 2000 character limit for custom command responses to prevent Nitro users from adding longer responses than a Discord bot can send (:issue:`5499`)

Dev Cog
*******

- ``[p]mockmsg`` now allows mocking attachment-only messages (:issue:`5446`)

Downloader
**********

- Added repo name to the response of ``[p]findcog`` command (:issue:`5382`, :issue:`5383`)

Economy
*******

- ``[p]economyset showsettings`` now includes configured role payday amounts (:issue:`5455`, :issue:`5457`)

General
*******

- Removed voice region field from ``[p]serverinfo`` command as Discord no longer provides this setting for servers (:issue:`5449`)

Mod
***

- ``[p]voicekick`` now sends a response when the action succeeds (:issue:`5367`)
- Fixed an error with ``[p]tempban`` failing to send an invite link when a server has an unset vanity URL (:issue:`5472`)
- Fixed explanations of example usage for ``[p]ban``, ``[p]kick``, and ``[p]tempban`` commands (:issue:`5372`)
- Fixed a typo in one of ``[p]unban``'s error messages (:issue:`5470`)

Modlog
******

- Added the new native Discord timestamps in ``[p]case``, ``[p]casesfor``, and ``[p]listcases`` commands (:issue:`5395`)

Warnings
********

- Warning actions no longer error out when the action is set to use a command that *only* checks for user permissions, not caller's roles (:issue:`5477`)


Developer changelog
-------------------

- Added optional ``message`` argument to `Context.tick()` and `Context.react_quietly()` which is used if adding the reaction doesn't succeed (:issue:`3359`, :issue:`4092`)
- Added optional ``check_permissions`` keyword-only argument to `Red.embed_requested()` which, if ``True``, will make the method also check whether the bot can send embeds in the given channel (:issue:`5452`)
- Added `Red.get_invite_url()` and `Red.is_invite_url_public()` that expose the functionality of ``[p]invite`` programmatically (:issue:`5152`, :issue:`5424`)
- Changed the output of ``CORE__LOAD``, ``CORE__RELOAD``, and ``CORE__UNLOAD`` RPC methods to a dictionary (:issue:`5451`, :issue:`5453`)


Documentation changes
---------------------

- Added install guide for Alma Linux 8.4-8.x and Raspberry Pi OS 11 Bullseye (:issue:`5440`)
- Updated the Java distribution used in the Windows install guide to Temurin - rebranded AdoptOpenJDK (:issue:`5403`)
- Improved Mac and pyenv instructions to address common issues with load path configuration (:issue:`5356`)
- Updated the server locations for Hetzner and Contabo in :ref:`host-list` document (:issue:`5475`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5447`)
- Removed inaccurate note from Unix install guides about install commands also being used for updating Red (:issue:`5439`)
- Removed LXC from unsupported hosting platforms as many VPS providers utilize that technology (:issue:`5351`)
- Specified that Red currently requires Python 3.8.1 - 3.9.x (:issue:`5403`)


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


Redbot 3.4.13 (2021-09-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Arman0334`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`fredster33`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`qenu`, :ghuser:`TheDataLeek`, :ghuser:`Twentysix26`, :ghuser:`TwinDragon`, :ghuser:`Vexed01`

Read before updating
--------------------

1. If you're hosting a public/big bot (>75 servers) or strive to scale your bot at that level, you should read :doc:`our stance on (privileged) intents and public bots <intents>`.
2. Fedora 32 is no longer supported as it has already reached end of life.
3. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

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


Redbot 3.4.12 (2021-06-17)
==========================

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


Redbot 3.4.11 (2021-06-12)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Onii-Chan-Discord`

This is a hotfix release fixing a crash involving guild uploaded stickers.

Full changelog
--------------

- discord.py version has been bumped to 1.7.3 (:issue:`5129`)
- Links to the CogBoard in Red's documentation have been updated to use the new domain (:issue:`5124`)


Redbot 3.4.10 (2021-05-28)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`benno1237`, :ghuser:`bobloy`, :ghuser:`BoyDownTown`, :ghuser:`Danstr5544`, :ghuser:`DeltaXWizard`, :ghuser:`Drapersniper`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Lifeismana`, :ghuser:`Obi-Wan3`, :ghuser:`OofChair`, :ghuser:`palmtree5`, :ghuser:`plofts`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`

Read before updating
--------------------

1. PM2 process manager is no longer supported as it is not a viable solution due to certain parts of its behavior.

    We highly recommend you to switch to one of the other supported solutions:
        - `autostart_systemd`
        - `autostart_mac`

    If you experience any issues when trying to configure it, you can join `our discord server <https://discord.gg/red>`__ and ask in the **support** channel for help.
2. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

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

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.8 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1212>`__.

2. Fedora 31 and OpenSUSE Leap 15.1 are no longer supported as they have already reached end of life.


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


Redbot 3.4.7 (2021-02-26)
=========================
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


Redbot 3.4.6 (2021-02-16)
=========================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`Andeeeee`, :ghuser:`bobloy`, :ghuser:`BreezeQS`, :ghuser:`Danstr5544`, :ghuser:`Dav-Git`, :ghuser:`Elysweyr`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`NeuroAssassin`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Strafee`, :ghuser:`TheWyn`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

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


Redbot 3.4.5 (2020-12-24)
=========================
| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Injabie3`, :ghuser:`NeuroAssassin`

End-user changelog
------------------

Streams
*******

- Fixed Streams failing to load and work properly (:issue:`4687`, :issue:`4688`)


Redbot 3.4.4 (2020-12-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreus7`, :ghuser:`NeuroAssassin`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.4 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.2_1170>`__.

2. Ubuntu 16.04 is no longer supported as it will soon reach its end of life and it is no longer viable for us to maintain support for it.

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


Redbot 3.4.3 (2020-11-16)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`KianBral`, :ghuser:`maxbooiii`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

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


Redbot 3.4.2 (2020-10-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`

Read before updating
--------------------

1. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

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


Redbot 3.4.1 (2020-10-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`absj30`, :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`chloecormier`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Generaleoley`, :ghuser:`hisztendahl`, :ghuser:`jack1142`, :ghuser:`KaiGucci`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`NeuroAssassin`, :ghuser:`nfitzen`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`PythonTryHard`, :ghuser:`SharkyTheKing`, :ghuser:`Stonedestroyer`, :ghuser:`thisisjvgrace`, :ghuser:`TrustyJAID`, :ghuser:`TurnrDev`, :ghuser:`Vexed01`, :ghuser:`Vuks69`, :ghuser:`xBlynd`, :ghuser:`zephyrkul`

Read before updating
--------------------

1. This release fixes a security issue in Mod cog. See `Security changelog below <important-341-2>` for more information.
2. This Red update bumps discord.py to version 1.5.1, which explicitly requests Discord intents. Red requires all Privileged Intents to be enabled. More information can be found at :ref:`enabling-privileged-intents`.
3. Mutes functionality has been moved from the Mod cog to a new separate cog (Mutes) featuring timed and role-based mutes. If you were using it (or want to start now), you can load the new cog with ``[p]load mutes``. You can see the full `Mutes changelog below <important-341-1>`.
4. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

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
| 1. Red now allows users to set locale per guild, which requires 3rd-party cogs to set contextual locale manually in code ran outside of command's context. See the `Core Bot changelog below <important-dev-341-1>` for more information.

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


Redbot 3.4.0 (2020-08-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`DevilXD`, :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kablekompany`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`SharkyTheKing`, :ghuser:`thisisjvgrace`, :ghuser:`Tinonb`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`
|
| **Read before updating**:
| 1. Red 3.4 comes with support for data deletion requests. Bot owners should read `red_core_data_statement` to ensure they know what information about their users is stored by the bot.
| 2. Debian Stretch, Fedora 30 and lower, and OpenSUSE Leap 15.0 and lower are no longer supported as they have already reached end of life.
| 3. There's been a change in behavior of ``[p]tempban``. Look at `Mod changelog <important-340-1>` for full details.
| 4. There's been a change in behavior of announcements in Admin cog. Look at `Admin changelog <important-340-2>` for full details.
| 5. Red 3.4 comes with breaking changes for cog developers. Look at `Developer changelog <important-340-3>` for full details.

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
| 1. Red now offers cog disabling API, which should be respected by 3rd-party cogs in guild-related actions happening outside of command's context. See the `Core Bot changelog below <important-dev-340-1>` for more information.
| 2. Red now provides data request API, which should be supported by all 3rd-party cogs. See the changelog entries in the `Core Bot changelog below <important-dev-340-1>` for more information.

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
